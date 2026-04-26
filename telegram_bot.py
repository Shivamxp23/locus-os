# /opt/locus/telegram_bot.py — v5: Full brain-wired with thinking status + rich context

import os, json, logging, asyncio, httpx
from collections import defaultdict
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("locus-bot")

TOKEN          = os.getenv("TELEGRAM_TOKEN")
OWNER_ID       = int(os.getenv("TELEGRAM_OWNER_ID"))
API_URL        = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN  = os.getenv("LOCUS_SERVICE_TOKEN")
GROQ_KEY       = os.getenv("GROQ_API_KEY")
GROQ_WHISPER_KEY = os.getenv("GROQ_WHISPER_FOR_OBSIDIAN_API_KEY", GROQ_KEY)

api_headers = {"X-Service-Token": SERVICE_TOKEN}

MAX_HISTORY = 14
conversation_history: dict[int, list] = defaultdict(list)

def _add_to_history(uid: int, role: str, content: str):
    conversation_history[uid].append({"role": role, "content": content})
    if len(conversation_history[uid]) > MAX_HISTORY:
        conversation_history[uid] = conversation_history[uid][-MAX_HISTORY:]

def _get_history(uid: int) -> list:
    return list(conversation_history[uid])


# ─── Prompts ─────────────────────────────────────────────────────────────────

ROUTER_PROMPT = """Route Shivam's message. Return JSON only.

Actions:
- vault_search: searching notes/knowledge. field: "query"
- capture: saving idea/note. field: "text"
- create_task: add a task. fields: "title", "faction" (health/leverage/craft/expression), "priority" (1-10), "urgency" (1-10), "difficulty" (1-10)
- schedule: see today's schedule or what to work on
- redirect_to_pwa: logging check-ins, mood (these go in PWA)
- draft_content: draft a post/blog. field: "topic"
- converse: everything else

Return ONLY valid JSON. No markdown.

Examples:
"hi" → {"action":"converse"}
"what did I write about filmmaking" → {"action":"vault_search","query":"filmmaking"}
"note: idea about camera angles" → {"action":"capture","text":"idea about camera angles"}
"log my morning" → {"action":"redirect_to_pwa"}
"add task: finish API docs" → {"action":"create_task","title":"finish API docs","faction":"leverage","priority":6,"urgency":7,"difficulty":4}
"what should I work on" → {"action":"schedule"}
"""

EXTRACT_PROMPT = """From this conversation, extract insights. Return JSON only.

{
  "topics": ["list of topics discussed"],
  "projects_mentioned": ["project names"],
  "avoidance": "avoidance behavior if detected, else null",
  "insight": "behavioral insight if detected, else null",
  "trait": "personality trait revealed, else null",
  "emotional_state": "emotional state or null"
}

Return ONLY JSON."""


# ─── LLM ─────────────────────────────────────────────────────────────────────

async def call_groq(messages: list, model: str = "llama-3.3-70b-versatile", temperature: float = 0.5) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": model, "messages": messages, "temperature": temperature}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ─── Brain Context ────────────────────────────────────────────────────────────

async def get_brain_dump() -> dict:
    """Single call — fetches ALL context in parallel on the server side."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{API_URL}/api/v1/context/brain_dump", headers=api_headers)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        log.warning(f"Brain dump failed: {e}")
    return {
        "personality": {"traits": [], "patterns": [], "interests": [], "active_projects": [], "avoidances": []},
        "behavior":    {"recent_dcs": [], "last_evening_checkin": None, "avoided_recently": [], "mood_trend": None},
        "today":       {"dcs": None, "mode": None, "pending": ["morning","afternoon","evening","night"]},
        "pending_tasks": [],
        "qdrant":      {"points_count": 0},
    }

async def vault_search(query: str, limit: int = 6) -> list:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{API_URL}/api/v1/vector/search",
                params={"q": query, "limit": limit},
                headers=api_headers
            )
            if r.status_code == 200:
                return r.json().get("results", [])
    except Exception as e:
        log.warning(f"Vault search failed: {e}")
    return []


# ─── System Prompt Builder ────────────────────────────────────────────────────

def build_system_prompt(brain: dict, vault_results: list = None) -> str:
    p   = brain.get("personality", {})
    b   = brain.get("behavior", {})
    t   = brain.get("today", {})
    tasks = brain.get("pending_tasks", [])
    q   = brain.get("qdrant", {})

    prompt = """You are Locus — Shivam's personal cognitive operating system and second brain.
Personality: Direct. Honest. Data-oriented. Not a cheerleader. Will call out avoidance patterns.
Like a trusted advisor who has read every journal entry, every note, every task.
This is Telegram — be thorough but readable. Use bullet points, not walls of text.
Always cite your reasoning. If you spotted a pattern, say so explicitly.\n\n"""

    if p.get("traits"):
        prompt += f"**Traits:** {', '.join(p['traits'])}\n"
    if p.get("patterns"):
        prompt += f"**Patterns:** {'; '.join(p['patterns'][:5])}\n"
    if p.get("interests"):
        prompt += f"**Interests:** {', '.join(p['interests'][:10])}\n"
    if p.get("active_projects"):
        prompt += f"**Active projects:** {', '.join(p['active_projects'])}\n"
    if p.get("avoidances"):
        prompt += f"**Known avoidances:** {'; '.join(p['avoidances'][:4])}\n"
    prompt += "\n"

    dcs  = t.get("dcs")
    mode = t.get("mode")
    if dcs:
        prompt += f"**Today — DCS:** {dcs} | **Mode:** {mode}\n"
    else:
        prompt += "**DCS not logged yet today** — morning check-in pending.\n"

    pending_ci = t.get("pending", [])
    if pending_ci:
        prompt += f"**Pending check-ins:** {', '.join(pending_ci)}\n"

    if b.get("recent_dcs"):
        prompt += f"**Last 7 days DCS:** {' | '.join(b['recent_dcs'][:5])}\n"
    if b.get("mood_trend"):
        prompt += f"**Mood trend:** {b['mood_trend']}\n"
    if b.get("last_evening_checkin"):
        prompt += f"**Last evening:** {b['last_evening_checkin'][:300]}\n"
    if b.get("avoided_recently"):
        prompt += f"**Avoided recently:** {', '.join(b['avoided_recently'][:3])}\n"

    if tasks:
        prompt += f"\n**Top pending tasks ({len(tasks)} total):**\n"
        faction_e = {"health":"🟢","leverage":"🔵","craft":"🟠","expression":"🟣"}
        for task in tasks[:5]:
            e = faction_e.get(task.get("faction",""),"⚪")
            prompt += f"  {e} {task['title']} (TWS:{task.get('tws','?')}, D:{task.get('difficulty','?')})\n"

    if vault_results:
        prompt += f"\n**Vault context ({len(vault_results)} relevant notes):**\n"
        for i, res in enumerate(vault_results[:4], 1):
            pl = res.get("payload", {})
            filename = pl.get("filename", "unknown")
            summary  = pl.get("summary") or pl.get("text","")[:300]
            score    = res.get("score", 0)
            prompt += f"\n[Note {i} — {filename} (relevance: {score:.2f})]:\n{summary}\n"

    prompt += f"\n**Vault indexed notes:** {q.get('points_count', 0)}\n"
    prompt += """
Rules:
- If vault results are provided above, USE them. Quote specific notes. Name the file.
- If you spot avoidance, call it out directly but constructively.
- Connect dots across projects and interests.
- If DCS is low, adjust your expectations of what to suggest.
- Be specific, not generic. Vague advice is useless.
- Direct the user to locusapp.online for check-ins and task logging.
"""
    return prompt


# ─── Thinking Status ─────────────────────────────────────────────────────────

async def update_thinking(msg, step: str):
    """Edit the thinking message with current step."""
    try:
        await msg.edit_text(step)
    except Exception:
        pass


# ─── Routing ─────────────────────────────────────────────────────────────────

async def route(text: str) -> dict:
    content = await call_groq(
        [{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": text}],
        model="llama-3.1-8b-instant",
        temperature=0
    )
    try:
        return json.loads(content)
    except Exception:
        return {"action": "converse"}


# ─── Core Conversation ───────────────────────────────────────────────────────

async def converse(text: str, uid: int, brain: dict, vault_results: list = None) -> str:
    system_prompt = build_system_prompt(brain, vault_results)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_get_history(uid))
    messages.append({"role": "user", "content": text})

    reply = await call_groq(messages, model="llama-3.3-70b-versatile", temperature=0.65)

    _add_to_history(uid, "user", text)
    _add_to_history(uid, "assistant", reply)

    asyncio.create_task(_learn(text, reply))
    return reply


async def _learn(user_msg: str, bot_reply: str):
    try:
        extraction = await call_groq(
            [{"role": "system", "content": EXTRACT_PROMPT},
             {"role": "user", "content": f"User: {user_msg}\n\nLocus: {bot_reply}"}],
            model="llama-3.1-8b-instant", temperature=0
        )
        extracted = json.loads(extraction)
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"{API_URL}/api/v1/context/learn",
                json={"extracted": extracted, "user_message": user_msg[:500], "bot_reply": bot_reply[:500]},
                headers=api_headers
            )
    except Exception as e:
        log.warning(f"Learning loop failed (non-fatal): {e}")


# ─── Owner Guard ──────────────────────────────────────────────────────────────

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper


# ─── Command Handlers ─────────────────────────────────────────────────────────

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Locus v5 — Brain Online*\n\n"
        "Every message I receive, I:\n"
        "1. Pull your personality graph from Neo4j\n"
        "2. Check behavioral patterns from Postgres\n"
        "3. Search your Obsidian vault in Qdrant\n"
        "4. Then think — and respond with all of that context.\n\n"
        "Commands: /status /brain /schedule /sync /clear\n"
        "Log check-ins & tasks → locusapp.online",
        parse_mode="Markdown"
    )

@owner_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🧠 Fetching brain status...")
    brain = await get_brain_dump()
    p = brain.get("personality", {})
    t = brain.get("today", {})
    b = brain.get("behavior", {})
    q = brain.get("qdrant", {})

    dcs  = t.get("dcs")
    mode = t.get("mode")
    text = "🧠 *Brain Status*\n\n"
    text += f"📊 DCS: {dcs or 'not logged'}" + (f" — {mode}" if mode else "") + "\n"
    pending = t.get("pending", [])
    if pending:
        text += f"⏳ Pending check-ins: {', '.join(pending)}\n"
    text += f"\n🧬 Traits: {len(p.get('traits',[]))}\n"
    text += f"🔄 Patterns: {len(p.get('patterns',[]))}\n"
    text += f"💡 Interests: {len(p.get('interests',[]))}\n"
    text += f"📁 Active projects: {len(p.get('active_projects',[]))}\n"
    text += f"⚠️ Avoidances tracked: {len(p.get('avoidances',[]))}\n"
    text += f"📚 Vault notes indexed: {q.get('points_count', 0)}\n"
    if b.get("mood_trend"):
        text += f"\n📈 Mood trend: {b['mood_trend']}\n"
    tasks = brain.get("pending_tasks", [])
    text += f"✅ Pending tasks: {len(tasks)}\n"
    text += f"💬 Messages in memory: {len(conversation_history.get(update.effective_user.id, []))}"
    await msg.edit_text(text, parse_mode="Markdown")

@owner_only
async def cmd_brain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Full brain dump — detailed view of everything Locus knows."""
    msg = await update.message.reply_text("🧠 Fetching full brain dump...")
    brain = await get_brain_dump()
    p = brain.get("personality", {})
    b = brain.get("behavior", {})
    t = brain.get("today", {})
    tasks = brain.get("pending_tasks", [])
    q = brain.get("qdrant", {})

    sections = ["🧠 *Full Brain Dump*\n"]

    # Neo4j
    sections.append("*── Neo4j Personality Graph ──*")
    sections.append(f"Traits: {', '.join(p.get('traits',[])) or 'none yet'}")
    sections.append(f"Patterns: {'; '.join(p.get('patterns',[])[:4]) or 'none yet'}")
    sections.append(f"Projects: {', '.join(p.get('active_projects',[])) or 'none'}")
    sections.append(f"Avoidances: {'; '.join(p.get('avoidances',[])[:3]) or 'none detected'}")
    sections.append(f"Interests: {', '.join(p.get('interests',[])[:8]) or 'none'}")

    # Postgres
    sections.append("\n*── Postgres Behavioral Data ──*")
    sections.append(f"DCS today: {t.get('dcs','not logged')} ({t.get('mode','')})")
    sections.append(f"Last 7 days: {' | '.join(b.get('recent_dcs',[])[:5]) or 'no data'}")
    sections.append(f"Mood trend: {b.get('mood_trend','unknown')}")
    sections.append(f"Last evening: {b.get('last_evening_checkin','none')[:200] if b.get('last_evening_checkin') else 'none'}")
    sections.append(f"Avoided recently: {', '.join(b.get('avoided_recently',[])) or 'nothing logged'}")

    # Tasks
    sections.append(f"\n*── Tasks (top {min(5,len(tasks))} of {len(tasks)} pending) ──*")
    faction_e = {"health":"🟢","leverage":"🔵","craft":"🟠","expression":"🟣"}
    for task in tasks[:5]:
        e = faction_e.get(task.get("faction",""),"⚪")
        sections.append(f"  {e} {task['title']} (TWS:{task.get('tws','?')})")

    # Qdrant
    sections.append(f"\n*── Qdrant Vault ──*")
    sections.append(f"Notes indexed: {q.get('points_count', 0)} | Status: {q.get('status','unknown')}")

    await msg.edit_text("\n".join(sections), parse_mode="Markdown")

@owner_only
async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📅 Building schedule...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{API_URL}/api/v1/schedule/today", headers=api_headers)
            if r.status_code == 200:
                data = r.json()
                await msg.edit_text(data.get("formatted", "No schedule yet."))
                return
    except Exception:
        pass
    await msg.edit_text("Schedule unavailable — log your morning check-in first.")

@owner_only
async def cmd_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Trigger vault enrichment + Qdrant indexing."""
    msg = await update.message.reply_text("🔄 Triggering vault sync...")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{API_URL}/api/v1/vault/enrich", headers=api_headers)
            if r.status_code == 200:
                await msg.edit_text(
                    "✅ Vault enrichment started in background.\n"
                    "New notes will be indexed into Qdrant over the next few minutes.\n"
                    "Check /status in a bit for updated point count."
                )
                return
    except Exception as e:
        pass
    await msg.edit_text("⚠️ Sync trigger failed — check if the API is up.")

@owner_only
async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conversation_history[update.effective_user.id] = []
    await update.message.reply_text("Memory cleared. Fresh start.")


# ─── Main Message Handler ────────────────────────────────────────────────────

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await process_text(update.message.text, update.effective_user.id, update)

@owner_only
async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    voice_file = update.message.voice or update.message.audio
    if not voice_file:
        return

    msg = await update.message.reply_text("🎙️ Transcribing...")
    try:
        file = await ctx.bot.get_file(voice_file.file_id)
        audio_bytes = await file.download_as_bytearray()

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_WHISPER_KEY}"},
                files={"file": ("voice.ogg", bytes(audio_bytes), "audio/ogg")},
                data={"model": "whisper-large-v3-turbo"}
            )
        if r.status_code == 200:
            text = r.json().get("text", "")
            await msg.edit_text(f"🎙️ *Transcribed:* {text}", parse_mode="Markdown")
            await process_text(text, update.effective_user.id, update)
        else:
            await msg.edit_text("🎙️ Transcription failed.")
    except Exception as e:
        log.error(f"Voice error: {e}")
        await msg.edit_text("🎙️ Transcription failed.")


async def process_text(text: str, uid: int, update: Update):
    # ── Step 1: Show thinking status immediately ──
    thinking_msg = await update.message.reply_text("🧠 Thinking...")

    try:
        # ── Step 2: Route the message ──
        action = await route(text)
        a = action.get("action", "converse")

        # ── Step 3: Gather brain context (always) ──
        await update_thinking(thinking_msg,
            "🧠 Thinking...\n├ Pulling personality (Neo4j)...\n├ Checking behavior (Postgres)...\n└ ...")

        brain = await get_brain_dump()

        p = brain.get("personality", {})
        qdrant_count = brain.get("qdrant", {}).get("points_count", 0)

        # ── Step 4: Action-specific handling ──

        if a == "vault_search":
            query = action.get("query", text)
            await update_thinking(thinking_msg,
                f"🧠 Thinking...\n├ Brain context ✓\n├ Searching vault: '{query}'...\n└ ...")

            results = await vault_search(query, limit=6)
            count = len(results)

            await update_thinking(thinking_msg,
                f"🧠 Thinking...\n├ Brain context ✓\n├ Vault search: {count} results ✓\n└ Composing response...")

            if results:
                reply = await converse(text, uid, brain, vault_results=results)
            else:
                # No results — tell the LLM the search was empty
                augmented = (
                    f"[SYSTEM: Vault search for '{query}' returned 0 results "
                    f"({qdrant_count} notes indexed). Answer from memory if possible, "
                    f"and suggest the user add notes on this topic.]\n\nUser: {text}"
                )
                reply = await converse(augmented, uid, brain)

            await thinking_msg.delete()
            await update.message.reply_text(reply)

        elif a == "capture":
            capture_text = action.get("text", text)
            await update_thinking(thinking_msg, "📝 Saving capture...")
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        f"{API_URL}/api/v1/captures",
                        json={"text": capture_text, "source": "telegram"},
                        headers=api_headers
                    )
                if r.status_code == 200:
                    await thinking_msg.edit_text(f"✅ Captured & indexed into vault:\n_{capture_text}_", parse_mode="Markdown")
                else:
                    await thinking_msg.edit_text("⚠️ Capture failed — API may be down.")
            except Exception:
                await thinking_msg.edit_text("⚠️ Capture failed — API may be down.")

        elif a == "create_task":
            await update_thinking(thinking_msg, "📌 Creating task...")
            task_data = {
                "title":      action.get("title", text[:100]),
                "faction":    action.get("faction", "craft"),
                "priority":   min(10, max(1, action.get("priority", 5))),
                "urgency":    min(10, max(1, action.get("urgency", 5))),
                "difficulty": min(10, max(1, action.get("difficulty", 5))),
            }
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(f"{API_URL}/api/v1/tasks", json=task_data, headers=api_headers)
                if r.status_code == 200:
                    data = r.json()
                    faction_e = {"health":"🟢","leverage":"🔵","craft":"🟠","expression":"🟣"}
                    e = faction_e.get(task_data["faction"],"⚪")
                    await thinking_msg.edit_text(
                        f"✅ Task created\n{e} *{task_data['title']}*\n"
                        f"TWS: {data.get('tws','?')} | {task_data['faction']}",
                        parse_mode="Markdown"
                    )
                else:
                    await thinking_msg.edit_text("⚠️ Task creation failed.")
            except Exception as e:
                await thinking_msg.edit_text(f"⚠️ Task creation error: {e}")

        elif a == "draft_content":
            topic = action.get("topic", text)
            await update_thinking(thinking_msg,
                f"✍️ Drafting content about: *{topic}*\n(Pulling context from Neo4j & Postgres...)",
            )
            try:
                import sys
                backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
                if backend_path not in sys.path:
                    sys.path.append(backend_path)
                from services.content_engine import generate_draft
                draft = await generate_draft(topic)
                await thinking_msg.delete()
                await update.message.reply_text(draft)
            except Exception as e:
                await thinking_msg.edit_text(f"⚠️ Draft failed: {e}")

        elif a == "schedule":
            await update_thinking(thinking_msg, "📅 Building schedule...")
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    r = await client.get(f"{API_URL}/api/v1/schedule/today", headers=api_headers)
                if r.status_code == 200:
                    data = r.json()
                    await thinking_msg.delete()
                    await update.message.reply_text(data.get("formatted", "No schedule yet."))
                else:
                    await thinking_msg.edit_text("Schedule endpoint unavailable.")
            except Exception:
                await thinking_msg.edit_text("Schedule unavailable.")

        elif a == "redirect_to_pwa":
            await thinking_msg.edit_text("📱 Log that at *locusapp.online*", parse_mode="Markdown")

        else:  # converse
            await update_thinking(thinking_msg,
                "🧠 Thinking...\n├ Brain context ✓\n└ Composing response...")

            reply = await converse(text, uid, brain)
            await thinking_msg.delete()
            await update.message.reply_text(reply)

    except Exception as e:
        log.error(f"process_text error: {e}")
        try:
            await thinking_msg.edit_text(f"⚠️ Error: {e}")
        except Exception:
            pass


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("brain",    cmd_brain))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("sync",     cmd_sync))
    app.add_handler(CommandHandler("clear",    cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    log.info("Locus bot v5 started — full brain-wired with thinking status.")
    app.run_polling()

if __name__ == "__main__":
    main()
