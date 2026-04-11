"""
Locus Telegram Bot — v2 (context-driven)

Architecture:
  Every message → build_context() queries all databases in parallel
               → Groq synthesizes with real data injected
               → learn_from_interaction() writes insights back (background)

The LLM is the reasoning engine. The databases are the memory.
Nothing is hardcoded. All personality context comes from Neo4j + Postgres.
"""

import os, json, logging, asyncio, httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

TOKEN         = os.getenv("TELEGRAM_TOKEN")
OWNER_ID      = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
API_URL       = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")
GROQ_KEY      = os.getenv("GROQ_API_KEY", "")

api_headers = {"X-Service-Token": SERVICE_TOKEN}


# ──────────────────────────────────────────────────────────────
#  PROMPTS
# ──────────────────────────────────────────────────────────────

ROUTER_PROMPT = """\
You are a routing agent for Shivam's personal second brain system.
Classify the message into exactly one action. Return ONLY valid JSON. No explanation. No markdown. No backticks.

Actions:
- vault_search   → explicit request to find notes ("what did I write about X", "find my notes on Y", "search for Z")
- wiki_query     → deep conceptual question that needs the compiled knowledge base
- capture        → saving an idea ("note: X", "remember: X", "capture: X")
- redirect_to_pwa → logging mood, energy, check-ins, tasks ("log my mood", "morning check-in", "add a task")
- converse       → EVERYTHING else: greetings, venting, questions, thinking out loud, status updates

Examples:
"hi"                              → {"action":"converse"}
"what did I write about filmmaking" → {"action":"vault_search","query":"filmmaking"}
"explain stoicism to me"          → {"action":"wiki_query","query":"stoicism"}
"I feel unmotivated today"        → {"action":"converse"}
"note: call the bank tomorrow"    → {"action":"capture","text":"call the bank tomorrow"}
"log my mood"                     → {"action":"redirect_to_pwa"}
"how many API tokens do I have"   → {"action":"converse"}
"""

# Dynamic — {context} is filled at runtime from databases
SYSTEM_TEMPLATE = """\
You are Locus — Shivam's personal cognitive operating system and second brain. Not a chatbot. Not an assistant. His second brain.

PERSONALITY:
- Direct, blunt, no filler. Never say "Great question!" or "Certainly!" or "Of course!".
- Talk like a trusted friend who has known him for years and has read everything he's ever written.
- Short when short is right. Longer when depth is needed. Never pad.
- Push back when he is wrong or avoiding something obvious.
- If you notice a pattern in his data, name it — don't wait to be asked.
- If your context has no relevant data, say so plainly: "I don't have enough data on that yet."

RULES:
- Only make claims grounded in the CONTEXT DATA below. Do not invent.
- If he asks for something you don't have data for, say you don't have it.
- If he wants to log mood/energy/tasks, redirect to locusapp.online — once, briefly.
- Do not fabricate numbers, scores, or technical details you weren't given.
- If context is empty, say the databases are still building up and you'll get smarter as data accumulates.

CONTEXT DATA (from your databases — use this to inform every response):
────────────────────────────────
{context}
────────────────────────────────
"""

EXTRACT_PROMPT = """\
Extract structured insights from this conversation exchange. Return ONLY valid JSON. No explanation. No markdown.

User said: {user_message}
Locus replied: {bot_reply}

Return exactly this structure:
{{
  "topics": ["list of specific topics or domains mentioned, e.g. filmmaking, stoicism, Locus"],
  "projects_mentioned": ["project names if any, e.g. Locus OS, Monevo"],
  "avoidance": "what the user seems to be avoiding or procrastinating on, or null if not present",
  "insight": "one specific behavioral or personality insight about Shivam from this exchange, or null",
  "trait": "one personality trait revealed, e.g. 'tends to overthink before starting', or null"
}}
"""


# ──────────────────────────────────────────────────────────────
#  GROQ CALL
# ──────────────────────────────────────────────────────────────

async def call_groq(messages: list, temperature: float = 0, max_tokens: int = 600) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ──────────────────────────────────────────────────────────────
#  CONTEXT BUILDER — queries all databases in parallel
# ──────────────────────────────────────────────────────────────

async def build_context(user_message: str) -> str:
    """
    Fires three requests in parallel:
      - Neo4j personality graph
      - PostgreSQL behavioral data
      - ChromaDB vault search (relevant to current message)

    Returns a formatted context string for injection into the system prompt.
    """
    async with httpx.AsyncClient(timeout=8) as client:
        # Fire all three in parallel
        personality_coro = client.get(
            f"{API_URL}/api/v1/context/personality",
            headers=api_headers
        )
        behavior_coro = client.get(
            f"{API_URL}/api/v1/context/recent_behavior",
            headers=api_headers
        )
        vault_coro = client.get(
            f"{API_URL}/api/v1/vault/search",
            params={"q": user_message},
            headers=api_headers
        )

        responses = {}
        for key, coro in [("personality", personality_coro),
                           ("behavior", behavior_coro),
                           ("vault", vault_coro)]:
            try:
                r = await coro
                if r.status_code == 200:
                    responses[key] = r.json()
            except Exception as e:
                log.warning(f"Context fetch [{key}] failed: {e}")

    parts = []

    # ── Personality from Neo4j ──
    p = responses.get("personality", {})
    if p.get("traits"):
        parts.append(f"PERSONALITY TRAITS: {', '.join(p['traits'])}")
    if p.get("patterns"):
        parts.append("OBSERVED BEHAVIOURAL PATTERNS:\n" +
                     "\n".join(f"  • {pat}" for pat in p["patterns"]))
    if p.get("interests"):
        parts.append(f"KNOWN INTERESTS: {', '.join(p['interests'])}")
    if p.get("active_projects"):
        parts.append(f"ACTIVE PROJECTS: {', '.join(p['active_projects'])}")
    if p.get("avoidances"):
        parts.append("KNOWN AVOIDANCES (recurring):\n" +
                     "\n".join(f"  • {a}" for a in p["avoidances"]))

    # ── Behavioral data from PostgreSQL ──
    b = responses.get("behavior", {})
    if b.get("recent_dcs"):
        parts.append("RECENT DCS / COGNITIVE STATE (last 7 days):\n" +
                     "\n".join(f"  {d}" for d in b["recent_dcs"]))
    if b.get("last_evening_checkin"):
        parts.append(f"LAST EVENING CHECK-IN: {b['last_evening_checkin']}")
    if b.get("avoided_recently"):
        parts.append(f"RECENTLY AVOIDED (14 days): {', '.join(b['avoided_recently'])}")
    if b.get("mood_trend"):
        parts.append(f"MOOD TREND: {b['mood_trend']}")

    # ── Relevant vault notes from ChromaDB ──
    vault_results = responses.get("vault", {}).get("results", [])
    if vault_results:
        note_lines = []
        for note in vault_results[:3]:
            note_lines.append(f"  [{note['title']}]\n  {note['excerpt']}")
        parts.append("RELEVANT NOTES FROM YOUR VAULT:\n" + "\n\n".join(note_lines))

    if not parts:
        return (
            "No context data yet. Neo4j personality graph is empty, PostgreSQL has no check-in data, "
            "and ChromaDB has no indexed notes. Tell Shivam to run 'mempalace mine /vault' and do a morning "
            "check-in — the system will get smarter as data accumulates."
        )

    return "\n\n".join(parts)


# ──────────────────────────────────────────────────────────────
#  LEARNING LOOP — runs in background after every conversation
# ──────────────────────────────────────────────────────────────

async def learn_from_interaction(user_message: str, bot_reply: str):
    """
    Uses a separate Groq call (low temperature) to extract structured insights
    from the exchange, then writes them to Neo4j via the /context/learn endpoint.

    Runs as a background asyncio task — never blocks the user-facing response.
    """
    try:
        prompt = EXTRACT_PROMPT.format(
            user_message=user_message,
            bot_reply=bot_reply
        )
        raw = await call_groq(
            [{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300
        )

        # Strip any accidental markdown fences
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        extracted = json.loads(raw)

        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{API_URL}/api/v1/context/learn",
                json={
                    "user_message": user_message,
                    "bot_reply": bot_reply,
                    "extracted": extracted
                },
                headers=api_headers
            )

        log.info(f"Learning write-back: {extracted}")

    except json.JSONDecodeError:
        log.warning(f"Failed to parse extracted insights: {raw[:200]}")
    except Exception as e:
        log.warning(f"learn_from_interaction failed: {e}")


# ──────────────────────────────────────────────────────────────
#  ROUTING
# ──────────────────────────────────────────────────────────────

async def route(text: str) -> dict:
    raw = await call_groq(
        [{"role": "system", "content": ROUTER_PROMPT},
         {"role": "user",   "content": text}],
        temperature=0,
        max_tokens=80
    )
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"action": "converse"}


# ──────────────────────────────────────────────────────────────
#  HANDLERS
# ──────────────────────────────────────────────────────────────

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper


@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Locus online.\n\n"
        "I have access to your vault, personality graph, and behavioral data. "
        "I get smarter the more you use the system.\n\n"
        "Search notes, capture ideas, think out loud.\n"
        "Log check-ins and tasks → locusapp.online"
    )


@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    log.info(f"Message: {text[:80]}")

    # Route
    try:
        action = await route(text)
    except Exception as e:
        await update.message.reply_text(f"Routing error: {e}")
        return

    a = action.get("action", "converse")
    reply = None

    # ── VAULT SEARCH ──
    if a == "vault_search":
        query = action.get("query", text)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{API_URL}/api/v1/vault/search",
                    params={"q": query},
                    headers=api_headers
                )
            if r.status_code == 200:
                results = r.json().get("results", [])
            else:
                results = []
        except Exception:
            results = []

        if not results:
            # Vault empty or unavailable — fall through to a conversational response
            context = await build_context(text)
            system = SYSTEM_TEMPLATE.format(context=context)
            reply = await call_groq(
                [{"role": "system", "content": system},
                 {"role": "user",   "content": f"I searched my vault for '{query}' but found nothing. What do you know about this from any other context?"}],
                temperature=0.5
            )
        else:
            lines = [f"📄 *{r['title']}*\n{r['excerpt']}" for r in results[:3]]
            reply = "\n\n".join(lines)

    # ── WIKI QUERY ──
    elif a == "wiki_query":
        query = action.get("query", text)
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(
                    f"{API_URL}/api/v1/wiki/query",
                    params={"q": query},
                    headers=api_headers
                )
            answer = r.json().get("answer", "") if r.status_code == 200 else ""
        except Exception:
            answer = ""

        if answer and "still compiling" not in answer:
            reply = answer
        else:
            # Wiki not ready — use vault search + conversation instead
            context = await build_context(text)
            system = SYSTEM_TEMPLATE.format(context=context)
            reply = await call_groq(
                [{"role": "system", "content": system},
                 {"role": "user",   "content": text}],
                temperature=0.6
            )

    # ── CAPTURE ──
    elif a == "capture":
        cap_text = action.get("text", text)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{API_URL}/api/v1/captures",
                    json={"text": cap_text, "source": "telegram"},
                    headers=api_headers
                )
            reply = "Captured ✓"
        except Exception as e:
            reply = f"Capture failed: {e}"

    # ── REDIRECT TO PWA ──
    elif a == "redirect_to_pwa":
        reply = "That goes in locusapp.online — all check-ins and tasks live there."

    # ── CONVERSE (main path) ──
    else:
        context = await build_context(text)
        system = SYSTEM_TEMPLATE.format(context=context)
        reply = await call_groq(
            [{"role": "system", "content": system},
             {"role": "user",   "content": text}],
            temperature=0.7
        )

    # Send reply
    if reply:
        await update.message.reply_text(reply, parse_mode="Markdown")

    # Background learning — does not block the response
    if reply and a not in ("capture", "redirect_to_pwa"):
        asyncio.create_task(learn_from_interaction(text, reply))


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Locus bot v2 started.")
    app.run_polling()


if __name__ == "__main__":
    main()
