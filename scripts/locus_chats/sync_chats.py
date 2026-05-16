#!/usr/bin/env python3
"""
Nightly headless sync for Locus Chat Vault.

Reads /vault/.browser_profiles/ for session state, fetches chat metadata and
full contents via REST API, writes Markdown to /vault/chats/, and maintains
/vault/.chat_manifest.json for incremental diff tracking.

Environment variables (optional but recommended):
    LOCUS_TG_TOKEN   – Telegram bot token
    LOCUS_TG_CHAT_ID – Telegram chat ID for alerts
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Gemini is async-only via gemini-webapi
# ---------------------------------------------------------------------------
try:
    from gemini_webapi import GeminiClient
except ImportError:
    GeminiClient = None  # type: ignore

# ---------------------------------------------------------------------------
# Config & logging
# ---------------------------------------------------------------------------
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/home/ubuntu/scripts/locus_chats/config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(log_file: str) -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Telegram alerts
# ---------------------------------------------------------------------------
def send_telegram(message: str) -> None:
    token = os.environ.get("LOCUS_TG_TOKEN")
    chat_id = os.environ.get("LOCUS_TG_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=15)
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------
def load_manifest(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    if not text:
        return "untitled"
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text) or "untitled"


def fmt_ts(ts: Any) -> str:
    """Normalise a timestamp to ISO-8601 UTC."""
    if ts is None:
        return "unknown"
    if isinstance(ts, str):
        # Already a string; try to parse & re-format
        try:
            # Handle Z suffix
            s = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return ts
    if isinstance(ts, (int, float)):
        # Assume seconds since epoch (ChatGPT uses this)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(ts)


def account_slug(email: str) -> str:
    return email.split("@")[0]


def platform_dir(vault: str, platform: str, slug: str) -> str:
    d = os.path.join(vault, platform, slug)
    os.makedirs(d, exist_ok=True)
    return d


def write_markdown(
    platform: str,
    account: str,
    chat_id: str,
    title: Optional[str],
    created: Any,
    updated: Any,
    messages: List[dict],
    vault_dir: str,
) -> str:
    """Write a single chat as Markdown. Returns filename."""
    slug = slugify(title)
    short_id = chat_id[:8]
    filename = f"{slug}-{short_id}.md"
    out_dir = platform_dir(vault_dir, platform, account_slug(account))
    filepath = os.path.join(out_dir, filename)

    # Delete old file if it exists with a different name (manifest rename handling)
    # (handled by caller)

    lines = [
        "---",
        f'title: "{title or "Untitled"}"',
        f"platform: {platform}",
        f"account: {account}",
        f"chat_id: {chat_id}",
        f"created: {fmt_ts(created)}",
        f"updated: {fmt_ts(updated)}",
        "---",
        "",
        f"# {title or 'Untitled'}",
        "",
    ]

    for msg in messages:
        sender = msg.get("sender", "unknown")
        ts = msg.get("time", "unknown")
        text = msg.get("text", "")

        if sender in ("human", "user"):
            emoji = "🧑 You"
        else:
            if platform == "claude":
                emoji = "🤖 Claude"
            elif platform == "chatgpt":
                emoji = "🤖 ChatGPT"
            elif platform == "gemini":
                emoji = "🤖 Gemini"
            elif platform == "aistudio":
                emoji = "🤖 AI Studio"
            elif platform == "perplexity":
                emoji = "🤖 Perplexity"
            elif platform == "flow":
                emoji = "🤖 Flow"
            else:
                emoji = "🤖 Assistant"

        lines.extend([
            f"## {emoji}",
            f"*{fmt_ts(ts)}*",
            "",
            text,
            "",
            "---",
            "",
        ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename


# ---------------------------------------------------------------------------
# Playwright token extraction
# ---------------------------------------------------------------------------
def extract_claude_token(context) -> Optional[str]:
    cookies = context.cookies("https://claude.ai")
    for c in cookies:
        if c.get("name") == "sessionKey":
            return c.get("value")
    return None


def extract_chatgpt_token(page) -> Optional[str]:
    token: List[Optional[str]] = [None]

    def handler(request):
        if token[0] is None and "backend-api" in request.url:
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token[0] = auth.split(" ", 1)[1]

    page.on("request", handler)
    page.goto("https://chatgpt.com", wait_until="networkidle")
    page.wait_for_timeout(3000)

    # If nothing intercepted yet, try to trigger an API call manually.
    if token[0] is None:
        try:
            page.evaluate(
                """async () => {
                    try {
                        await fetch('/backend-api/conversations?offset=0&limit=1');
                    } catch(e) {}
                }"""
            )
            page.wait_for_timeout(3000)
        except Exception:
            pass

    return token[0]


def extract_gemini_cookies(context) -> Tuple[Optional[str], Optional[str]]:
    cookies = context.cookies("https://gemini.google.com")
    psid = None
    psidts = None
    for c in cookies:
        name = c.get("name", "")
        if name == "__Secure-1PSID":
            psid = c.get("value")
        elif name == "__Secure-1PSIDTS":
            psidts = c.get("value")
    return psid, psidts


def extract_perplexity_cookies(context) -> Dict[str, str]:
    """Return all perplexity.ai cookies as a dict; sync caller uses them all."""
    cookies = context.cookies("https://perplexity.ai")
    return {c["name"]: c["value"] for c in cookies if "value" in c}


def extract_flow_cookies(context) -> Dict[str, str]:
    """Return all flow/microsoft cookies as a dict."""
    # Try a few possible domains
    all_cookies: List[dict] = []
    for domain in ("https://flow.microsoft.com", "https://copilot.microsoft.com", "https://www.bing.com"):
        all_cookies.extend(context.cookies(domain))
    # dedupe by name
    result = {}
    for c in all_cookies:
        if "value" in c:
            result[c["name"]] = c["value"]
    return result


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http_json(url: str, headers: dict, timeout: int = 30) -> Tuple[Optional[Any], int]:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        return (r.json() if r.text else None), r.status_code
    except requests.exceptions.JSONDecodeError:
        return None, r.status_code
    except Exception as e:
        logging.error(f"HTTP error for {url}: {e}")
        return None, 0


# ---------------------------------------------------------------------------
# Platform sync implementations
# ---------------------------------------------------------------------------
class SyncRunner:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.vault_dir = cfg["vault_dir"]
        self.profiles_dir = cfg["profiles_dir"]
        self.manifest_path = cfg["manifest_path"]
        self.manifest = load_manifest(self.manifest_path)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

    # -----------------------------------------------------------------------
    # Manifest helpers per-platform
    # -----------------------------------------------------------------------
    def get_manifest_entry(self, platform: str, account: str, chat_id: str) -> Optional[dict]:
        return self.manifest.get(platform, {}).get(account_slug(account), {}).get(chat_id)

    def set_manifest_entry(self, platform: str, account: str, chat_id: str, entry: dict) -> None:
        self.manifest.setdefault(platform, {}).setdefault(account_slug(account), {})[chat_id] = entry

    def delete_old_file(self, platform: str, account: str, old_filename: str) -> None:
        if not old_filename:
            return
        path = os.path.join(self.vault_dir, platform, account_slug(account), old_filename)
        if os.path.exists(path):
            os.remove(path)

    # -----------------------------------------------------------------------
    # Claude
    # -----------------------------------------------------------------------
    def sync_claude(self, account: str, token: str, force_full: bool) -> int:
        headers = {"Cookie": f"sessionKey={token}"}
        orgs, status = http_json("https://claude.ai/api/organizations", headers)
        if status in (401, 403):
            return -1  # signal auth failure
        if not orgs or not isinstance(orgs, list):
            logging.warning(f"[claude/{account}] No organisations found.")
            return 0

        org_id = orgs[0].get("uuid")
        if not org_id:
            return 0

        # Paginate conversations
        all_convs: List[dict] = []
        offset = 0
        while True:
            url = f"https://claude.ai/api/organizations/{org_id}/conversations?limit=50&offset={offset}"
            batch, status = http_json(url, headers)
            if status in (401, 403):
                return -1
            if not batch or not isinstance(batch, list):
                break
            all_convs.extend(batch)
            if len(batch) < 50:
                break
            offset += 50

        if not all_convs:
            return 0

        updated = 0
        for conv in all_convs:
            conv_id = conv.get("uuid")
            updated_at = conv.get("updated_at")
            if not conv_id:
                continue

            existing = self.get_manifest_entry("claude", account, conv_id)
            if not force_full and existing and existing.get("updated_at") == updated_at:
                continue

            # Fetch full conversation
            detail, status = http_json(
                f"https://claude.ai/api/organizations/{org_id}/conversations/{conv_id}",
                headers,
            )
            if status in (401, 403):
                return -1
            if not detail or not isinstance(detail, dict):
                continue

            messages = []
            for msg in detail.get("chat_messages", []):
                messages.append(
                    {
                        "sender": msg.get("sender", "unknown"),
                        "time": msg.get("created_at"),
                        "text": msg.get("text", ""),
                    }
                )

            title = detail.get("name") or detail.get("title")
            created = detail.get("created_at")
            filename = write_markdown(
                "claude", account, conv_id, title, created, updated_at, messages, self.vault_dir
            )

            if existing and existing.get("filename") and existing["filename"] != filename:
                self.delete_old_file("claude", account, existing["filename"])

            self.set_manifest_entry(
                "claude",
                account,
                conv_id,
                {
                    "updated_at": updated_at,
                    "turns": len(messages),
                    "filename": filename,
                },
            )
            updated += 1

        return updated

    # -----------------------------------------------------------------------
    # ChatGPT
    # -----------------------------------------------------------------------
    def sync_chatgpt(self, account: str, token: str, force_full: bool) -> int:
        headers = {"Authorization": f"Bearer {token}"}
        all_convs: List[dict] = []
        offset = 0
        total_expected = None

        while True:
            url = f"https://chatgpt.com/backend-api/conversations?offset={offset}&limit=50&order=updated"
            data, status = http_json(url, headers)
            if status in (401, 403):
                return -1
            if not data or not isinstance(data, dict):
                break
            if total_expected is None:
                total_expected = data.get("total")
            items = data.get("items", [])
            if not items:
                break
            all_convs.extend(items)
            if len(items) < 50:
                break
            offset += 50
            if total_expected is not None and len(all_convs) >= total_expected:
                break

        if not all_convs:
            return 0

        updated = 0
        for conv in all_convs:
            conv_id = conv.get("id")
            updated_at = conv.get("update_time")
            if not conv_id:
                continue

            existing = self.get_manifest_entry("chatgpt", account, conv_id)
            if not force_full and existing and existing.get("updated_at") == updated_at:
                continue

            detail, status = http_json(
                f"https://chatgpt.com/backend-api/conversation/{conv_id}", headers
            )
            if status in (401, 403):
                return -1
            if not detail or not isinstance(detail, dict):
                continue

            mapping = detail.get("mapping", {})
            messages = self._linearize_chatgpt_mapping(mapping)

            title = conv.get("title")
            created = conv.get("create_time")
            filename = write_markdown(
                "chatgpt", account, conv_id, title, created, updated_at, messages, self.vault_dir
            )

            if existing and existing.get("filename") and existing["filename"] != filename:
                self.delete_old_file("chatgpt", account, existing["filename"])

            self.set_manifest_entry(
                "chatgpt",
                account,
                conv_id,
                {
                    "updated_at": updated_at,
                    "turns": len(messages),
                    "filename": filename,
                },
            )
            updated += 1

        return updated

    def _linearize_chatgpt_mapping(self, mapping: dict) -> List[dict]:
        # Find root node (parent == None)
        root_id = None
        for k, v in mapping.items():
            if v is None:
                continue
            if v.get("parent") is None:
                root_id = k
                break

        results: List[dict] = []

        def walk(node_id: str):
            node = mapping.get(node_id)
            if not node or not isinstance(node, dict):
                return
            msg = node.get("message")
            if msg and isinstance(msg, dict):
                author = msg.get("author", {})
                role = author.get("role", "unknown")
                content = msg.get("content", {})
                parts = content.get("parts", []) if isinstance(content, dict) else []
                text = "\n".join(str(p) for p in parts if p)
                create_time = msg.get("create_time")
                results.append(
                    {
                        "sender": role,
                        "time": create_time,
                        "text": text,
                    }
                )
            for child in node.get("children", []):
                walk(child)

        if root_id:
            walk(root_id)
        return results

    # -----------------------------------------------------------------------
    # Gemini
    # -----------------------------------------------------------------------
    def sync_gemini(self, account: str, cookies: Tuple[Optional[str], Optional[str]], force_full: bool) -> int:
        psid, psidts = cookies
        if not psid:
            return -1

        async def _async_sync() -> int:
            if GeminiClient is None:
                logging.error("gemini-webapi not installed.")
                return 0

            # Build cookie dict for the client
            cookie_dict = {"__Secure-1PSID": psid}
            if psidts:
                cookie_dict["__Secure-1PSIDTS"] = psidts

            client = GeminiClient()
            # The library may accept cookies during init or via set_cookies;
            # we attempt the most common pattern.
            try:
                await client.init(cookie_dict, timeout=30, auto_close=False)
            except Exception as e:
                logging.error(f"[gemini/{account}] Client init failed: {e}")
                return 0

            try:
                chats = await client.list_chats()
            except Exception as e:
                logging.error(f"[gemini/{account}] list_chats failed: {e}")
                return 0

            if not chats:
                return 0

            updated = 0
            for chat in chats:
                chat_id = chat.id if hasattr(chat, "id") else chat.get("id")
                title = chat.title if hasattr(chat, "title") else chat.get("title")
                if not chat_id:
                    continue

                # Gemini does not expose updated_at; use turn count for diffing
                try:
                    history = await client.read_chat(chat_id)
                except Exception as e:
                    logging.warning(f"[gemini/{account}] read_chat({chat_id}) failed: {e}")
                    continue

                turns = history.turns if hasattr(history, "turns") else history.get("turns", [])
                turn_count = len(turns)

                existing = self.get_manifest_entry("gemini", account, chat_id)
                if not force_full and existing and existing.get("turns") == turn_count:
                    continue

                messages = []
                for turn in turns:
                    user_query = turn.user_query if hasattr(turn, "user_query") else turn.get("user_query", "")
                    model_resp = turn.model_response if hasattr(turn, "model_response") else turn.get("model_response")
                    resp_text = ""
                    if model_resp:
                        if hasattr(model_resp, "text"):
                            resp_text = model_resp.text
                        elif isinstance(model_resp, dict):
                            resp_text = model_resp.get("text", "")

                    # Timestamps are not always available per-turn in gemini-webapi;
                    # we record null and let fmt_ts handle it.
                    if user_query:
                        messages.append({"sender": "user", "time": None, "text": str(user_query)})
                    if resp_text:
                        messages.append({"sender": "model", "time": None, "text": str(resp_text)})

                filename = write_markdown(
                    "gemini", account, chat_id, title, None, None, messages, self.vault_dir
                )

                if existing and existing.get("filename") and existing["filename"] != filename:
                    self.delete_old_file("gemini", account, existing["filename"])

                self.set_manifest_entry(
                    "gemini",
                    account,
                    chat_id,
                    {
                        "updated_at": None,
                        "turns": turn_count,
                        "filename": filename,
                    },
                )
                updated += 1

            return updated

        return asyncio.run(_async_sync())

    # -----------------------------------------------------------------------
    # Google AI Studio
    # -----------------------------------------------------------------------
    def sync_aistudio(self, account: str, cookies: Tuple[Optional[str], Optional[str]], force_full: bool) -> int:
        """
        AI Studio sync — best-effort.

        Primary: internal API endpoints (need runtime discovery).
        Fallback: Google Drive 'AI Studio' folder via authenticated web API.
        """
        psid, psidts = cookies
        if not psid:
            return -1

        cookie_header = f"__Secure-1PSID={psid}"
        if psidts:
            cookie_header += f"; __Secure-1PSIDTS={psidts}"
        headers = {"Cookie": cookie_header}

        # ---- Attempt 1: known internal endpoints (may change) ----
        # These are placeholders — verify with DevTools Network tab.
        known_list_urls = [
            "https://aistudio.google.com/api/projects",
            "https://aistudio.google.com/api/prompts",
        ]

        for list_url in known_list_urls:
            data, status = http_json(list_url, headers, timeout=15)
            if status == 200 and data:
                logging.info(f"[aistudio/{account}] Found working list endpoint: {list_url}")
                # We don't yet know the exact schema; log and alert.
                send_telegram(
                    f"⚠️ aistudio/{account} returned data from {list_url} but parser is not implemented. "
                    "Verify the JSON schema and update sync_aistudio()."
                )
                return 0

        # ---- Attempt 2: Google Drive web fallback ----
        # Search for Drive folder named "AI Studio" using the authenticated session.
        # The internal Drive API is complex; we attempt the lightweight search endpoint.
        logging.info(f"[aistudio/{account}] Trying Google Drive web fallback…")
        drive_search = (
            "https://drive.google.com/drive/search?q=title:'AI%20Studio'"
        )
        try:
            r = requests.get(drive_search, headers={"Cookie": cookie_header}, timeout=15)
            # Response is HTML; we'd need to parse JSON embedded in the page or use
            # the batched internal RPC. This is intentionally left as a documented stub
            # because the exact internal protocol changes frequently.
            if r.status_code == 200:
                logging.warning(
                    f"[aistudio/{account}] Drive search returned HTML. "
                    "A full Drive RPC parser is required for automated export."
                )
        except Exception as e:
            logging.warning(f"[aistudio/{account}] Drive fallback error: {e}")

        logging.warning(
            f"[aistudio/{account}] No automated endpoint implemented. "
            "Please record internal API calls via DevTools and update the script."
        )
        return 0

    # -----------------------------------------------------------------------
    # Perplexity
    # -----------------------------------------------------------------------
    def sync_perplexity(self, account: str, cookies: Dict[str, str], force_full: bool) -> int:
        """
        Perplexity sync — best-effort based on current internal API shape.
        Verify endpoints with DevTools during setup if these fail.
        """
        if not cookies:
            return -1

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers = {"Cookie": cookie_header}

        # Try likely conversation-list endpoints
        list_urls = [
            "https://www.perplexity.ai/api/library",
            "https://www.perplexity.ai/api/threads",
            "https://www.perplexity.ai/api/conversations",
        ]

        all_convs = None
        used_list_url = None
        for url in list_urls:
            data, status = http_json(url, headers, timeout=15)
            if status in (401, 403):
                return -1
            if status == 200 and data and isinstance(data, (list, dict)):
                # Some endpoints return {"threads": [...]}
                if isinstance(data, dict):
                    candidate = data.get("threads") or data.get("conversations") or data.get("items") or data.get("data")
                else:
                    candidate = data
                if candidate and isinstance(candidate, list):
                    all_convs = candidate
                    used_list_url = url
                    break

        if all_convs is None:
            logging.warning(
                f"[perplexity/{account}] Could not find a working conversation list endpoint. "
                "Verify via DevTools and update list_urls in sync_perplexity()."
            )
            return 0

        if not all_convs:
            return 0

        updated = 0
        for conv in all_convs:
            # Schema guesses — verify at runtime.
            conv_id = conv.get("id") or conv.get("thread_id") or conv.get("conversation_id")
            updated_at = conv.get("updated_at") or conv.get("last_updated") or conv.get("updated_time")
            title = conv.get("title") or conv.get("name") or "Untitled"
            if not conv_id:
                continue

            existing = self.get_manifest_entry("perplexity", account, conv_id)
            if not force_full and existing and existing.get("updated_at") == updated_at:
                continue

            # Try detail endpoints
            detail = None
            for tmpl in [
                f"https://www.perplexity.ai/api/thread/{conv_id}",
                f"https://www.perplexity.ai/api/threads/{conv_id}",
                f"https://www.perplexity.ai/api/conversation/{conv_id}",
            ]:
                d, status = http_json(tmpl, headers, timeout=15)
                if status in (401, 403):
                    return -1
                if status == 200 and d:
                    detail = d
                    break

            if not detail or not isinstance(detail, dict):
                logging.warning(f"[perplexity/{account}] No detail endpoint worked for {conv_id}.")
                continue

            messages = self._parse_perplexity_detail(detail)
            filename = write_markdown(
                "perplexity", account, conv_id, title, None, updated_at, messages, self.vault_dir
            )

            if existing and existing.get("filename") and existing["filename"] != filename:
                self.delete_old_file("perplexity", account, existing["filename"])

            self.set_manifest_entry(
                "perplexity",
                account,
                conv_id,
                {
                    "updated_at": updated_at,
                    "turns": len(messages),
                    "filename": filename,
                },
            )
            updated += 1

        return updated

    def _parse_perplexity_detail(self, detail: dict) -> List[dict]:
        """Attempt multiple known response shapes."""
        messages: List[dict] = []

        # Shape A: { queries: [...], answers: [...] }
        queries = detail.get("queries") or detail.get("questions") or []
        answers = detail.get("answers") or detail.get("responses") or []
        if queries and answers:
            for i, q in enumerate(queries):
                text = q if isinstance(q, str) else q.get("text", "")
                ts = q.get("timestamp") if isinstance(q, dict) else None
                messages.append({"sender": "user", "time": ts, "text": str(text)})
                if i < len(answers):
                    a = answers[i]
                    atext = a if isinstance(a, str) else a.get("text", "")
                    ats = a.get("timestamp") if isinstance(a, dict) else None
                    messages.append({"sender": "assistant", "time": ats, "text": str(atext)})
            return messages

        # Shape B: { messages: [ {role, content, timestamp}, ... ] }
        msgs = detail.get("messages") or detail.get("history") or []
        if msgs and isinstance(msgs, list):
            for m in msgs:
                role = m.get("role", "unknown")
                content = m.get("content") or m.get("text", "")
                if isinstance(content, list):
                    content = "\n".join(str(x) for x in content)
                ts = m.get("timestamp") or m.get("created_at")
                messages.append({"sender": role, "time": ts, "text": str(content)})
            return messages

        # Shape C: { turns: [...] }
        turns = detail.get("turns") or detail.get("steps") or []
        if turns and isinstance(turns, list):
            for t in turns:
                user = t.get("query") or t.get("question") or ""
                bot = t.get("answer") or t.get("response") or ""
                ts = t.get("timestamp") or t.get("updated_at")
                if user:
                    messages.append({"sender": "user", "time": ts, "text": str(user)})
                if bot:
                    messages.append({"sender": "assistant", "time": ts, "text": str(bot)})
            return messages

        return messages

    # -----------------------------------------------------------------------
    # Flow (Microsoft)
    # -----------------------------------------------------------------------
    def sync_flow(self, account: str, cookies: Dict[str, str], force_full: bool) -> int:
        """
        Flow sync — best-effort. Microsoft restructures products frequently.
        Verify the correct login URL, product name, and API endpoints at runtime.
        """
        if not cookies:
            return -1

        # Flow may actually be Microsoft Copilot / Bing Chat. We attempt a few
        # known authenticated endpoints. Update these after DevTools inspection.
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers = {"Cookie": cookie_header}

        # Known possible history endpoints (verify at runtime)
        candidate_list_urls = [
            "https://copilot.microsoft.com/api/history",
            "https://www.bing.com/turing/conversation/chats",
            "https://flow.microsoft.com/api/conversations",
        ]

        all_convs = None
        for url in candidate_list_urls:
            data, status = http_json(url, headers, timeout=15)
            if status in (401, 403):
                return -1
            if status == 200 and data:
                if isinstance(data, list):
                    all_convs = data
                    break
                if isinstance(data, dict):
                    candidate = (
                        data.get("conversations")
                        or data.get("chats")
                        or data.get("threads")
                        or data.get("items")
                        or data.get("data")
                    )
                    if candidate and isinstance(candidate, list):
                        all_convs = candidate
                        break

        if all_convs is None:
            logging.warning(
                f"[flow/{account}] No working list endpoint found. "
                "Verify the correct product URL and API endpoints with DevTools, then update sync_flow()."
            )
            return 0

        if not all_convs:
            return 0

        updated = 0
        for conv in all_convs:
            conv_id = conv.get("id") or conv.get("conversationId") or conv.get("chatId")
            updated_at = conv.get("updatedAt") or conv.get("updated_at") or conv.get("lastUpdated")
            title = conv.get("title") or conv.get("name") or "Untitled"
            if not conv_id:
                continue

            existing = self.get_manifest_entry("flow", account, conv_id)
            if not force_full and existing and existing.get("updated_at") == updated_at:
                continue

            detail = None
            for tmpl in [
                f"https://copilot.microsoft.com/api/conversation/{conv_id}",
                f"https://www.bing.com/turing/conversation/{conv_id}",
                f"https://flow.microsoft.com/api/conversation/{conv_id}",
            ]:
                d, status = http_json(tmpl, headers, timeout=15)
                if status in (401, 403):
                    return -1
                if status == 200 and d:
                    detail = d
                    break

            if not detail or not isinstance(detail, dict):
                continue

            messages = self._parse_flow_detail(detail)
            filename = write_markdown(
                "flow", account, conv_id, title, None, updated_at, messages, self.vault_dir
            )

            if existing and existing.get("filename") and existing["filename"] != filename:
                self.delete_old_file("flow", account, existing["filename"])

            self.set_manifest_entry(
                "flow",
                account,
                conv_id,
                {
                    "updated_at": updated_at,
                    "turns": len(messages),
                    "filename": filename,
                },
            )
            updated += 1

        return updated

    def _parse_flow_detail(self, detail: dict) -> List[dict]:
        messages: List[dict] = []
        # Microsoft Copilot/Bing usually returns { messages: [...] }
        msgs = detail.get("messages") or detail.get("turns") or detail.get("history") or []
        if msgs and isinstance(msgs, list):
            for m in msgs:
                role = m.get("author") or m.get("role") or "unknown"
                text = m.get("text") or m.get("message") or m.get("content", "")
                if isinstance(text, dict):
                    text = text.get("text", "")
                ts = m.get("timestamp") or m.get("createdAt") or m.get("date")
                messages.append({"sender": role, "time": ts, "text": str(text)})
        return messages

    # -----------------------------------------------------------------------
    # Orchestration
    # -----------------------------------------------------------------------
    def run(self, force_full: bool = False) -> None:
        if not force_full:
            force_full = self._is_vault_empty()
            if force_full:
                logging.info("Empty vault detected — forcing full export of all conversations.")

        total_updated = 0
        active_combos = 0
        zero_alert_candidates: List[str] = []

        for platform in self.cfg["platforms"]:
            for account in self.cfg["accounts"]:
                slug = account_slug(account)
                combo = f"{platform}/{slug}"

                # Exclusion list
                excluded = any(
                    e.get("platform") == platform and e.get("account") == slug
                    for e in self.cfg.get("exclude", [])
                )
                if excluded:
                    logging.info(f"[{combo}] SKIP — excluded by config.")
                    continue

                profile_path = os.path.join(self.profiles_dir, f"{platform}_{slug}")
                if not os.path.exists(profile_path):
                    logging.info(
                        f"[{combo}] SKIP — no profile saved. "
                        f"Run: python setup_auth.py {platform} {slug}"
                    )
                    continue

                logging.info(f"[{combo}] Starting sync…")
                token_or_cookies = None

                # Launch Playwright headlessly to refresh & extract token
                try:
                    with sync_playwright() as p:
                        context = p.chromium.launch_persistent_context(profile_path, headless=True)
                        page = context.new_page()
                        try:
                            if platform == "claude":
                                page.goto("https://claude.ai/new", wait_until="domcontentloaded")
                                page.wait_for_timeout(2000)
                                token_or_cookies = extract_claude_token(context)
                            elif platform == "chatgpt":
                                token_or_cookies = extract_chatgpt_token(page)
                            elif platform == "gemini":
                                page.goto("https://gemini.google.com/app", wait_until="domcontentloaded")
                                page.wait_for_timeout(2000)
                                token_or_cookies = extract_gemini_cookies(context)
                            elif platform == "aistudio":
                                page.goto("https://aistudio.google.com", wait_until="domcontentloaded")
                                page.wait_for_timeout(2000)
                                token_or_cookies = extract_gemini_cookies(context)
                            elif platform == "perplexity":
                                page.goto("https://perplexity.ai", wait_until="domcontentloaded")
                                page.wait_for_timeout(2000)
                                token_or_cookies = extract_perplexity_cookies(context)
                            elif platform == "flow":
                                # Try multiple landing URLs
                                for url in ("https://copilot.microsoft.com", "https://flow.microsoft.com"):
                                    try:
                                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                                        page.wait_for_timeout(2000)
                                        break
                                    except Exception:
                                        pass
                                token_or_cookies = extract_flow_cookies(context)
                        finally:
                            context.close()
                except Exception as e:
                    logging.exception(f"[{combo}] Playwright token extraction failed: {e}")
                    send_telegram(f"⚠️ {combo} session extraction failed. Run: python setup_auth.py {platform} {slug}")
                    continue

                if token_or_cookies is None or (
                    isinstance(token_or_cookies, tuple) and token_or_cookies[0] is None
                ) or (isinstance(token_or_cookies, dict) and not token_or_cookies):
                    logging.warning(f"[{combo}] Token/cookie extraction returned empty — session expired?")
                    send_telegram(f"⚠️ {combo} session expired. Run: python setup_auth.py {platform} {slug}")
                    continue

                # Run platform-specific sync
                try:
                    if platform == "claude":
                        n = self.sync_claude(account, token_or_cookies, force_full)
                    elif platform == "chatgpt":
                        n = self.sync_chatgpt(account, token_or_cookies, force_full)
                    elif platform == "gemini":
                        n = self.sync_gemini(account, token_or_cookies, force_full)
                    elif platform == "aistudio":
                        n = self.sync_aistudio(account, token_or_cookies, force_full)
                    elif platform == "perplexity":
                        n = self.sync_perplexity(account, token_or_cookies, force_full)
                    elif platform == "flow":
                        n = self.sync_flow(account, token_or_cookies, force_full)
                    else:
                        n = 0
                except Exception as e:
                    logging.exception(f"[{combo}] Sync error: {e}")
                    n = 0

                if n == -1:
                    # Auth failure surfaced during API calls
                    logging.warning(f"[{combo}] API returned 401/403 — session expired.")
                    send_telegram(f"⚠️ {combo} session expired. Run: python setup_auth.py {platform} {slug}")
                    continue

                if n == 0:
                    zero_alert_candidates.append(combo)
                else:
                    total_updated += n
                    active_combos += 1
                    logging.info(f"[{combo}] {n} chat(s) updated.")

                # Persist manifest after each account/platform combo
                save_manifest(self.manifest_path, self.manifest)

        # Alert for zero-conversation combos where profile existed & token worked
        for combo in zero_alert_candidates:
            send_telegram(
                f"⚠️ {combo} — profile & token OK but 0 conversations exported. "
                "Possible API endpoint change or account has no history."
            )

        send_telegram(
            f"✅ Locus Chat Sync complete — {total_updated} chats updated across {active_combos} platform/account combinations."
        )
        logging.info(
            f"Sync finished. {total_updated} chats updated across {active_combos} combos."
        )

    def _is_vault_empty(self) -> bool:
        vault = Path(self.vault_dir)
        if not vault.exists():
            return True
        return len(list(vault.rglob("*.md"))) == 0


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Locus Chat Vault nightly sync")
    parser.add_argument(
        "--force-full",
        action="store_true",
        help="Ignore manifest and re-export everything",
    )
    parser.add_argument(
        "--config",
        default=CONFIG_PATH,
        help="Path to config.json",
    )
    args = parser.parse_args()

    cfg = load_config()
    cfg["_config_path"] = args.config
    setup_logging(cfg["log_file"])

    runner = SyncRunner(cfg)
    runner.run(force_full=args.force_full)


if __name__ == "__main__":
    main()
