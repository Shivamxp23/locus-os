# /opt/locus/telegram_bot.py — v4: Brain-wired with personality + learning loop + memory

import os
import json
import logging
import httpx
from collections import defaultdict
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("locus-bot")

TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID"))
API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_WHISPER_KEY = os.getenv("GROQ_WHISPER_FOR_OBSIDIAN_API_KEY", GROQ_KEY)

api_headers = {"X-Service-Token": SERVICE_TOKEN}

# ─── Conversation Memory ────────────────────────────────────
# Stores last N messages per user session (in-memory, resets on restart)
MAX_HISTORY = 12
conversation_history: dict[int, list] = defaultdict(list)


def _add_to_history(user_id: int, role: str, content: str):
    conversation_history[user_id].append({"role": role, "content": content})
    # Keep only last MAX_HISTORY messages
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]


def _get_history(user_id: int) -> list:
    return list(conversation_history[user_id])


# ─── Router Prompt ───────────────────────────────────────────
ROUTER_PROMPT = """Route Shivam's message. Return JSON only.

Actions:
- vault_search: searching notes/knowledge. field: "query"
- capture: saving idea/note. field: "text"  
- create_task: wants to add a task. fields: "title", "faction" (health/leverage/craft/expression), "priority" (1-10), "urgency" (1-10), "difficulty" (1-10)
- schedule: wants to see today's schedule or what to work on
- redirect_to_pwa: logging check-ins, mood (these go in PWA)
- draft_content: wants to draft a post (e.g. linkedin/IG) or blog. field: "topic"
- converse: everything else — questions, thoughts, venting, greetings

Return ONLY valid JSON. No markdown.

Examples:
"hi" → {"action":"converse"}
"what did I write about filmmaking" → {"action":"vault_search","query":"filmmaking"}
"Draft a linkedin post about building locus OS" → {"action":"draft_content","topic":"building locus OS"}
"why do I keep avoiding Monevo" → {"action":"vault_search","query":"Monevo avoidance patterns"}
"note: idea about camera angles" → {"action":"capture","text":"idea about camera angles"}
"log my morning" → {"action":"redirect_to_pwa"}
"add task: finish API docs" → {"action":"create_task","title":"finish API docs","faction":"leverage","priority":6,"urgency":7,"difficulty":4}
"what should I work on" → {"action":"schedule"}
"what's on my plate today" → {"action":"schedule"}
"I've been feeling stuck lately" → {"action":"converse"}
"""

# ─── Extraction Prompt ───────────────────────────────────────
EXTRACT_PROMPT = """From this conversation between Shivam and his AI (Locus), extract insights.
Return JSON with these fields (all optional, return null if not detected):

{
  "topics": ["list of topics/subjects discussed"],
  "projects_mentioned": ["project names mentioned"],
  "avoidance": "description of avoidance behavior if detected, else null",
  "insight": "behavioral/personality insight if detected, else null",
  "trait": "personality trait revealed if detected, else null",
  "emotional_state": "detected emotional state (frustrated, excited, anxious, etc) or null"
}

Return ONLY JSON. No explanation."""


# ─── Core LLM Call ───────────────────────────────────────────

async def call_groq(messages: list, model: str = "llama-3.3-70b-versatile", temperature: float = 0) -> str:
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ─── Brain Context Fetchers ──────────────────────────────────

async def get_personality_context() -> dict:
    """Fetch personality from Neo4j via FastAPI"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{API_URL}/api/v1/context/personality",
                headers=api_headers
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        log.warning(f"Personality context fetch failed: {e}")
    return {"traits": [], "patterns": [], "interests": [], "active_projects": [], "avoidances": []}


async def get_behavioral_context() -> dict:
    """Fetch recent behavioral data from PostgreSQL via FastAPI"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{API_URL}/api/v1/context/recent_behavior",
                headers=api_headers
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        log.warning(f"Behavioral context fetch failed: {e}")
    return {"recent_dcs": [], "last_evening_checkin": None, "avoided_recently": [], "mood_trend": None}


async def get_today_status() -> dict:
    """Fetch today's check-in status"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{API_URL}/api/v1/checkins/today",
                headers=api_headers
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        log.warning(f"Today status fetch failed: {e}")
    return {"dcs": None, "mode": None, "pending": ["morning", "afternoon", "evening", "night"]}


def build_system_prompt(personality: dict, behavior: dict, today: dict) -> str:
    """Build a rich, context-aware system prompt from all brain data"""

    # Base identity
    prompt = """You are Locus — Shivam's personal cognitive operating system and second brain.
Your personality: Direct. Honest. Data-oriented. Not a cheerleader. Will push back.
Like a trusted advisor who has read every journal entry he's written.
Keep responses concise — this is Telegram, not an essay.\n\n"""

    # Personality traits from Neo4j
    if personality.get("traits"):
        prompt += f"**Known personality traits:** {', '.join(personality['traits'])}\n"
    
    # Behavioral patterns from Neo4j
    if personality.get("patterns"):
        prompt += f"**Behavioral patterns observed:** {'; '.join(personality['patterns'][:4])}\n"

    # Active interests from Neo4j
    if personality.get("interests"):
        prompt += f"**Current interests:** {', '.join(personality['interests'][:10])}\n"

    # Active projects from Neo4j
    if personality.get("active_projects"):
        prompt += f"**Active projects:** {', '.join(personality['active_projects'])}\n"

    # Known avoidances from Neo4j
    if personality.get("avoidances"):
        prompt += f"**Known avoidances (be alert for these):** {'; '.join(personality['avoidances'][:3])}\n"

    prompt += "\n"

    # Today's status
    dcs = today.get("dcs")
    mode = today.get("mode")
    if dcs:
        prompt += f"**Today's DCS:** {dcs} — Mode: {mode}\n"
    else:
        prompt += "**DCS not logged yet today** — morning check-in pending.\n"

    pending = today.get("pending", [])
    if pending:
        prompt += f"**Pending check-ins:** {', '.join(pending)}\n"

    # Recent behavior from PostgreSQL
    if behavior.get("recent_dcs"):
        prompt += f"**Last 7 days DCS:** {' | '.join(behavior['recent_dcs'][:5])}\n"

    if behavior.get("mood_trend"):
        prompt += f"**Mood trend:** {behavior['mood_trend']}\n"

    if behavior.get("last_evening_checkin"):
        prompt += f"**Last evening check-in:** {behavior['last_evening_checkin'][:200]}\n"

    if behavior.get("avoided_recently"):
        prompt += f"**Avoided recently:** {', '.join(behavior['avoided_recently'][:3])}\n"

    prompt += """
Rules:
- If he asks about his notes → search the vault for him.
- If he wants to log/track → send him to locusapp.online.
- If you detect avoidance patterns → call them out directly but constructively.
- Connect dots across his projects and interests.
- Be genuinely useful. Ask sharp questions. Don't be sycophantic.
"""
    return prompt


# ─── Learning Write-back ─────────────────────────────────────

async def learn_from_conversation(user_message: str, bot_reply: str):
    """Extract insights from the conversation and write back to the brain"""
    try:
        # Use 8b for fast extraction
        extraction = await call_groq([
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": f"User: {user_message}\n\nLocus: {bot_reply}"}
        ], model="llama-3.1-8b-instant", temperature=0)

        try:
            extracted = json.loads(extraction)
        except json.JSONDecodeError:
            return  # Skip if extraction fails

        # POST to /context/learn — writes to Neo4j + PostgreSQL
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"{API_URL}/api/v1/context/learn",
                json={
                    "extracted": extracted,
                    "user_message": user_message[:500],
                    "bot_reply": bot_reply[:500]
                },
                headers=api_headers
            )
        log.info(f"Learning loop: extracted {len(extracted.get('topics', []))} topics, "
                 f"avoidance={'yes' if extracted.get('avoidance') else 'no'}")

    except Exception as e:
        log.warning(f"Learning loop failed (non-fatal): {e}")


# ─── Message Routing ─────────────────────────────────────────

async def route(text: str) -> dict:
    content = await call_groq([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": text}
    ], model="llama-3.1-8b-instant")  # 8b for routing — fast
    try:
        return json.loads(content)
    except:
        return {"action": "converse"}


# ─── Conversation with Full Brain ────────────────────────────

async def converse(text: str, user_id: int) -> str:
    """Full brain-wired conversation with personality context + memory"""

    # 1. Fetch all context from the brain (parallel-ish)
    personality = await get_personality_context()
    behavior = await get_behavioral_context()
    today = await get_today_status()

    # 2. Build rich system prompt
    system_prompt = build_system_prompt(personality, behavior, today)

    # 3. Build message list with history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(_get_history(user_id))
    messages.append({"role": "user", "content": text})

    # 4. Call 70b for real conversation
    reply = await call_groq(messages, model="llama-3.3-70b-versatile", temperature=0.6)

    # 5. Save to history
    _add_to_history(user_id, "user", text)
    _add_to_history(user_id, "assistant", reply)

    # 6. Learn from this conversation (fire-and-forget)
    # Don't await — let it run in background so user gets reply fast
    import asyncio
    asyncio.create_task(learn_from_conversation(text, reply))

    return reply


# ─── Owner Guard ─────────────────────────────────────────────

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper


# ─── Command Handlers ────────────────────────────────────────

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Locus v4 online — brain connected.\n\n"
        "I pull your personality, behavior patterns, and recent check-ins\n"
        "before every response. Every conversation teaches me more.\n\n"
        "Talk to me. Search your vault. Capture ideas.\n"
        "Log check-ins and tasks → locusapp.online"
    )


@owner_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show brain status — what the system knows right now"""
    personality = await get_personality_context()
    behavior = await get_behavioral_context()
    today = await get_today_status()

    msg = "🧠 **Brain Status**\n\n"

    dcs = today.get("dcs")
    mode = today.get("mode")
    if dcs:
        msg += f"📊 DCS: {dcs} — {mode}\n"
    else:
        msg += "📊 DCS: not logged yet\n"

    pending = today.get("pending", [])
    if pending:
        msg += f"⏳ Pending: {', '.join(pending)}\n"

    msg += f"\n🧬 Traits: {len(personality.get('traits', []))}\n"
    msg += f"🔄 Patterns: {len(personality.get('patterns', []))}\n"
    msg += f"💡 Interests: {len(personality.get('interests', []))}\n"
    msg += f"📁 Projects: {len(personality.get('active_projects', []))}\n"
    msg += f"⚠️ Avoidances: {len(personality.get('avoidances', []))}\n"

    if behavior.get("mood_trend"):
        msg += f"\n📈 Mood trend: {behavior['mood_trend']}\n"

    if behavior.get("avoided_recently"):
        msg += f"🚫 Avoided recently: {', '.join(behavior['avoided_recently'][:3])}\n"

    msg += f"\n💬 Messages in memory: {len(conversation_history.get(update.effective_user.id, []))}"

    await update.message.reply_text(msg, parse_mode="Markdown")


@owner_only
async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Get today's AI-generated schedule"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{API_URL}/api/v1/schedule/today",
                headers=api_headers
            )
            if r.status_code == 200:
                data = r.json()
                await update.message.reply_text(data.get("formatted", "No schedule generated yet."))
                return
    except:
        pass
    await update.message.reply_text("Schedule unavailable — use /checkin to log your morning first.")


@owner_only
async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Clear conversation memory"""
    conversation_history[update.effective_user.id] = []
    await update.message.reply_text("Memory cleared. Fresh start.")


# ─── Main Message Handler ────────────────────────────────────

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    await process_text(text, user_id, update)

@owner_only
async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    voice_file = update.message.voice or update.message.audio
    if not voice_file: return
    
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
            await msg.edit_text(f"🎙️: {text}")
            await process_text(text, update.effective_user.id, update)
        else:
            log.error(f"Whisper error: {r.text}")
            await msg.edit_text("🎙️ Transcription failed.")
    except Exception as e:
        log.error(f"Voice handling error: {e}")
        await msg.edit_text("🎙️ Transcription failed.")

async def process_text(text: str, user_id: int, update: Update):
    user_id = update.effective_user.id

    try:
        action = await route(text)
    except Exception as e:
        log.error(f"Routing error: {e}")
        await update.message.reply_text(f"Routing error: {e}")
        return

    a = action.get("action")

    if a == "vault_search":
        query = action.get("query", text)
        search_status = "unavailable"
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.get(
                    f"{API_URL}/api/v1/vault/search",
                    params={"q": query},
                    headers=api_headers
                )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                
                # Was there an explicit message from the API (like "Brain indexing")?
                api_msg = data.get("message")
                
                if results and results[0].get("excerpt"):
                    answer = results[0]["excerpt"]
                    # Truncate long vault results for Telegram
                    if len(answer) > 3000:
                        answer = answer[:3000] + "\n\n...(truncated)"
                    await update.message.reply_text(answer)
                    return
                elif api_msg:
                    search_status = f"unavailable (API said: {api_msg})"
                else:
                    search_status = "empty (no matches found)"
        except Exception as e:
            log.warning(f"Vault search failed: {e}")
            search_status = f"failed ({e})"

        # Fallback: converse about the topic, but explicitly inform the LLM the search failed
        reply = await converse(
            f"[SYSTEM: A vault search for '{query}' was attempted but returning '{search_status}'. "
            f"Please address the user's question directly based on your memory.]\nUser: {text}",
            user_id
        )
        await update.message.reply_text(reply)

    elif a == "capture":
        capture_text = action.get("text", text)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{API_URL}/api/v1/captures",
                    json={"text": capture_text, "source": "telegram"},
                    headers=api_headers
                )
            if r.status_code == 200:
                await update.message.reply_text("Captured ✓")
            else:
                await update.message.reply_text("Capture failed — API may be down.")
        except:
            await update.message.reply_text("Capture failed — API may be down.")

    elif a == "draft_content":
        topic = action.get("topic", text)
        msg_wait = await update.message.reply_text(f"✍️ Drafting content about: {topic}...\n(Pulling cognitive context from Neo4j & Postgres)")
        try:
            from services.content_engine import generate_draft
            draft = await generate_draft(topic)
            await msg_wait.edit_text(draft)
        except Exception as e:
            log.error(f"Drafting error: {e}")
            await msg_wait.edit_text(f"Failed to draft content: {str(e)}")

    elif a == "create_task":
        try:
            task_data = {
                "title": action.get("title", text[:100]),
                "faction": action.get("faction", "craft"),
                "priority": min(10, max(1, action.get("priority", 5))),
                "urgency": min(10, max(1, action.get("urgency", 5))),
                "difficulty": min(10, max(1, action.get("difficulty", 5))),
            }
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{API_URL}/api/v1/tasks",
                    json=task_data,
                    headers=api_headers
                )
            if r.status_code == 200:
                data = r.json()
                await update.message.reply_text(
                    f"Task created ✓\n"
                    f"📌 {task_data['title']}\n"
                    f"🏴 {task_data['faction']} | TWS: {data.get('tws', '?')}"
                )
            else:
                await update.message.reply_text("Task creation failed.")
        except Exception as e:
            await update.message.reply_text(f"Task creation failed: {e}")

    elif a == "schedule":
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{API_URL}/api/v1/schedule/today",
                    headers=api_headers
                )
            if r.status_code == 200:
                data = r.json()
                await update.message.reply_text(data.get("formatted", "No schedule yet — log your morning check-in first."))
            else:
                await update.message.reply_text("Schedule endpoint not available.")
        except:
            await update.message.reply_text("Schedule unavailable.")

    elif a == "redirect_to_pwa":
        await update.message.reply_text("Log that at locusapp.online")

    else:  # converse — full brain-wired conversation
        reply = await converse(text, user_id)
        await update.message.reply_text(reply)


# ─── Entry Point ─────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    log.info("Locus bot v4 started — brain-wired with personality + memory + learning loop.")
    app.run_polling()


if __name__ == "__main__":
    main()
