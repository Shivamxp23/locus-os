# Locus Chat Vault

Fully autonomous nightly cron system that exports chat histories from Claude, ChatGPT, Gemini, Google AI Studio, Perplexity, and Microsoft Flow into a local Markdown vault.

Runs headlessly on a Linux ARM64 server (Ubuntu 22.04, Oracle Cloud Free Tier) with zero human intervention after one-time browser authentication.

---

## Table of Contents

1. [Overview](#overview)
2. [File Layout](#file-layout)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [One-Time Authentication (`setup_auth.py`)](#one-time-authentication-setup_authpy)
6. [Nightly Sync (`sync_chats.py`)](#nightly-sync-sync_chatspy)
7. [Telegram Alerts](#telegram-alerts)
8. [Cron Job](#cron-job)
9. [First-Run Verification](#first-run-verification)
10. [Log Inspection](#log-inspection)
11. [Excluding a Platform/Account Combo](#excluding-a-platformaccount-combo)
12. [Disaster Recovery](#disaster-recovery)
13. [Platform Notes & Runtime Verification](#platform-notes--runtime-verification)

---

## Overview

The system maintains 30 possible platform/account combinations (6 platforms × 5 Google accounts). It uses **Playwright** only to capture browser sessions during a one-time headed login. Every night, a headless cron job reuses those saved profiles to extract session tokens, then fetches chat metadata and full contents via each platform's internal REST API. Results are written as individual Markdown files and tracked in a single JSON manifest for incremental diffing.

---

## File Layout

```
/home/ubuntu/scripts/locus_chats/
  setup_auth.py        ← headed login, saves browser profile
  sync_chats.py        ← headless nightly export
  config.json          ← accounts, platforms, exclusions, paths
  requirements.txt     ← Python dependencies
  README.md            ← this file

/vault/
  chats/
    claude/
      soni82003/
        Some-Chat-Title-a1b2c3d4.md
        ...
    chatgpt/ ...
    gemini/ ...
    aistudio/ ...
    perplexity/ ...
    flow/ ...
  .browser_profiles/
    claude_soni82003/
    chatgpt_soni82003/
    ... (30 folders max)
  .chat_manifest.json        ← incremental diff source-of-truth
```

---

## Prerequisites

- Ubuntu 22.04 LTS (ARM64)
- Python 3.10+ (system Python is fine)
- `curl`, `unzip`
- Internet egress (no inbound ports required)
- Telegram bot token + chat ID (optional but strongly recommended for alerts)

---

## Installation

Run all commands as the user that will own the cron job (e.g. `ubuntu`).

### 1. Install Python dependencies

```bash
sudo apt update
sudo apt install -y python3-pip curl unzip

# Install Python packages into system site-packages
pip3 install -r /home/ubuntu/scripts/locus_chats/requirements.txt --break-system-packages
```

### 2. Install Playwright Chromium (ARM64)

```bash
# Install system dependencies for Chromium
python3 -m playwright install-deps chromium

# Download Chromium browser binaries
python3 -m playwright install chromium
```

> On a fresh Oracle Cloud ARM64 instance, `install-deps` may require additional packages. If any errors appear, install the missing libraries and re-run.

### 3. Create vault directories

```bash
sudo mkdir -p /vault/chats /vault/.browser_profiles /var/log
sudo chown -R $(whoami):$(whoami) /vault /var/log
```

### 4. Review `config.json`

```bash
cat /home/ubuntu/scripts/locus_chats/config.json
```

Default contents are already correct for the five accounts and six platforms. Edit only if you need to change paths or add exclusions (see [Excluding a Platform/Account Combo](#excluding-a-platformaccount-combo)).

---

## One-Time Authentication (`setup_auth.py`)

You must run this once for every platform/account pair you want to back up. You only need to run it for combinations that **actually have an account** on the platform; the nightly sync silently skips any missing profiles.

### Syntax

```bash
cd /home/ubuntu/scripts/locus_chats
python3 setup_auth.py <platform> <account_slug>
```

`<account_slug>` is the part before `@` in the email address.

### Example — all 30 combinations

```bash
ACCOUNTS=(soni82003 soni820034 shivamsonifilms xodplisbo ekajuemail)
PLATFORMS=(claude chatgpt gemini aistudio perplexity flow)

for p in "${PLATFORMS[@]}"; do
  for a in "${ACCOUNTS[@]}"; do
    echo "=== $p / $a ==="
    python3 setup_auth.py "$p" "$a"
  done
done
```

### What happens

1. A **visible** Chromium window opens.
2. The platform login page loads.
3. **You** complete login manually (password, 2FA, Google SSO, CAPTCHA).
4. The script detects the authenticated landing URL and saves cookies + localStorage to `/vault/.browser_profiles/<platform>_<account>/`.
5. The browser closes automatically.

### Timeout / failure

If the login is not detected within **5 minutes**, the script prints:

```
Login did not complete within the 5-minute timeout. Possible causes:
2FA still pending, wrong account, CAPTCHA unsolved, or this account may
not exist on this platform. Check the browser window. Re-run this script
if you need to try again.
```

It exits with a non-zero status. No automatic retry or account creation occurs.

### Headless server tip

If your server has no GUI, either:

- Use SSH with X11 forwarding (`ssh -X ubuntu@host`) from a Linux/macOS client with an X server, or
- Use a VNC / remote-desktop session on the VM, or
- Run the script locally on your laptop, then `rsync` or `scp` the resulting profile folder from `/vault/.browser_profiles/` to the server.

---

## Nightly Sync (`sync_chats.py`)

Run manually for testing:

```bash
cd /home/ubuntu/scripts/locus_chats
python3 sync_chats.py
```

Force a full re-export (ignore manifest):

```bash
python3 sync_chats.py --force-full
```

### Behaviour

1. **Empty-vault check** — If `/vault/chats/` contains zero `.md` files, the manifest is ignored and everything is exported from scratch.
2. **Profile check** — Missing profiles are skipped silently with a log line.
3. **Token refresh** — For each saved profile, a headless Chromium context is launched, navigated to a lightweight authenticated page, and the required session cookie/token is extracted. Playwright is closed immediately.
4. **Incremental diff** — Conversation lists are fetched via REST. Only new or changed conversations (by `updated_at` or turn count) are re-fetched in full.
5. **Markdown export** — Each conversation is written atomically as a single `.md` file.
6. **Manifest update** — The in-memory manifest is updated per-conversation; the JSON file is atomically replaced (`tmp` + `os.replace`) after each platform/account combination finishes.
7. **Telegram summary** — A completion message is sent at the end.

---

## Telegram Alerts

Export two environment variables **before** running `sync_chats.py` (cron must also see them).

```bash
export LOCUS_TG_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
export LOCUS_TG_CHAT_ID="-1001234567890"
```

### What triggers an alert

- **Session expiry** — profile exists but token cannot be extracted or API returns `401/403`. Message includes the exact `setup_auth.py` command to fix it.
- **Zero conversations with valid token** — profile + token are healthy but the platform returns no conversations. This usually means the internal API endpoint changed and the script needs updating.
- **Nightly completion** — summary count of updated chats and active combos.

### What does NOT trigger an alert

- Missing profiles (expected for accounts not yet configured)
- Excluded combinations
- Nights where nothing changed because no new chats were created

### Persisting env vars for cron

Add the exports to the crontab command line or to a wrapper script, e.g. `/home/ubuntu/scripts/locus_chats/.env`:

```bash
# /home/ubuntu/scripts/locus_chats/.env
export LOCUS_TG_TOKEN="YOUR_TOKEN"
export LOCUS_TG_CHAT_ID="YOUR_CHAT_ID"
```

Then source it in cron:

```bash
0 2 * * * . /home/ubuntu/scripts/locus_chats/.env && /usr/bin/python3 /home/ubuntu/scripts/locus_chats/sync_chats.py >> /var/log/locus_chats.log 2>&1
```

---

## Cron Job

Open the crontab:

```bash
crontab -e
```

Add:

```bash
# Locus Chat Vault — nightly export at 02:00 UTC
0 2 * * * . /home/ubuntu/scripts/locus_chats/.env && /usr/bin/python3 /home/ubuntu/scripts/locus_chats/sync_chats.py >> /var/log/locus_chats.log 2>&1
```

Save and exit. The `.env` file is optional — you can also inline the variables.

---

## First-Run Verification

1. Run `setup_auth.py` for at least one platform/account you know has conversations.
2. Run `sync_chats.py` manually once.
3. Check the vault:

```bash
find /vault/chats -name "*.md" | head -n 20
```

4. Inspect a file:

```bash
cat /vault/chats/claude/soni82003/*.md | head -n 30
```

5. Check the manifest:

```bash
cat /vault/.chat_manifest.json | python3 -m json.tool | head -n 40
```

6. Verify Telegram received the completion message.

---

## Log Inspection

```bash
# Tail live logs during a manual run
tail -f /var/log/locus_chats.log

# Last 100 lines
sudo tail -n 100 /var/log/locus_chats.log

# Search for errors
grep -i "error\|skip\|expired\|fail" /var/log/locus_chats.log
```

---

## Excluding a Platform/Account Combo

If you confirm an account does **not** exist on a platform and never will, permanently silence it by editing `config.json`:

```bash
nano /home/ubuntu/scripts/locus_chats/config.json
```

Add to the `exclude` array:

```json
"exclude": [
  { "platform": "flow", "account": "xodplisbo" },
  { "platform": "perplexity", "account": "ekajuemail" }
]
```

Restart cron is not required; the change is read on the next sync run.

---

## Disaster Recovery

- **If the manifest is deleted** — `sync_chats.py` detects zero `.md` files in `/vault/chats/` only on an **empty vault**. If `.md` files still exist but the manifest is gone, run with `--force-full` to rebuild both the files and the manifest from scratch.
- **If profile cookies expire** — The nightly sync sends a Telegram alert with the exact `setup_auth.py` command. Re-run it.
- **If an API endpoint changes** — The script will export zero conversations despite a valid token and will alert you. Inspect the logs, open the platform in a browser with DevTools, record the new endpoint, and update the relevant function in `sync_chats.py`.

---

## Platform Notes & Runtime Verification

### Claude, ChatGPT, Gemini
These three are fully reverse-engineered and should work out of the box. Gemini uses the third-party `gemini-webapi` package; its internal cookie-refresh logic handles session renewal automatically.

### Google AI Studio
No stable public REST API exists at time of writing. The script attempts a few internal endpoints and falls back to a Google Drive web-search stub. **You must verify the correct endpoint via DevTools** (`aistudio.google.com` → Network tab → filter `api/`) and update `sync_aistudio()` if you need automated export. Conversations are also saved to a Drive folder called "AI Studio"; a full Drive-RPC parser is left as a documented stub.

### Perplexity
The script tries three likely list endpoints (`/api/library`, `/api/threads`, `/api/conversations`) and three detail patterns. **Verify with DevTools** during setup because Perplexity changes internal route names frequently. If none match, the script logs the failed URLs and sends a Telegram alert.

### Flow (Microsoft)
Microsoft rebrands and moves its AI chat products often. The script currently tries `copilot.microsoft.com` and `flow.microsoft.com` with several candidate API paths. **Verify the correct product URL and API endpoints** with DevTools before relying on this platform. Update `PLATFORMS` in `setup_auth.py` and `sync_flow()` in `sync_chats.py` if the URLs change.

---

## Technical Constraints Summary

| Constraint | Implementation |
|---|---|
| Python 3.10+ | System Python on Ubuntu 22.04 |
| Playwright + Chromium only | `p.chromium.launch_persistent_context(...)` |
| No Selenium / undetected-chromedriver | Not used |
| `requests` for HTTP | All sync calls; Gemini async wrapped in `asyncio.run()` |
| No database | Single JSON manifest only |
| No Docker | Native scripts |
| No port binding | Scripts only make outbound HTTPS |
| ARM64 | `chromium` Playwright channel; no x86-only deps |
| System pip | All installs use `--break-system-packages` |

---

## License

Internal project file — Locus OS.
