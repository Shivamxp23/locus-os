# /opt/locus/telegram_bot.py — v3 with 70b conversation + behavioral context

import os
import json
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID"))
API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

api_headers = {"X-Service-Token": SERVICE_TOKEN}

ROUTER_PROMPT = """Route Shivam's message. Return JSON only.

Actions:
- vault_search: searching notes/knowledge. field: "query"
- capture: saving idea/note. field: "text"  
- redirect_to_pwa: logging check-ins, tasks, mood (these go in PWA)
- converse: everything else — questions, thoughts, venting, greetings

Return ONLY valid JSON. No markdown.

Examples:
"hi" → {"action":"converse"}
"what did I write about filmmaking" → {"action":"vault_search","query":"filmmaking"}
"why do I keep avoiding Monevo" → {"action":"vault_search","query":"Monevo avoidance patterns"}
"note: idea about camera angles" → {"action":"capture","text":"idea about camera angles"}
"log my morning" → {"action":"redirect_to_pwa"}
"add a task" → {"action":"redirect_to_pwa"}
"I've been feeling stuck lately" → {"action":"converse"}
"""

CONVERSE_PROMPT = """You are Locus — Shivam's personal cognitive operating system and second brain.

About Shivam:
- 20-something building Locus (PCOS), Monevo (fintech), Stratmore Guild
- Interested in: cinematography, Roger Deakins, philosophy, AI, religion, self-optimization
- Uses a faction system: Health/Stability, Leverage/Money, Craft/Skills, Expression/Explore
- Tracks daily metrics: Energy, Mood, Sleep, Stress → Daily Capacity Score (DCS)
- His biggest pattern: avoids creative work on low-energy days, overcommits intellectually
- Current phase: building the infrastructure of his second brain

Your personality: Direct. Honest. Data-oriented. Not a cheerleader. Will push back. 
Like a trusted advisor who has read every journal entry he's written.

If he asks about his notes → suggest he ask you to search specifically.
If he wants to log anything → send him to locusapp.online (brief, not preachy).
Otherwise → be genuinely useful. Ask sharp questions. Connect dots across his projects.
Keep responses concise — this is Telegram, not an essay."""

async def get_behavioral_context() -> str:
    """Get recent behavioral data to inject into conversation"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{API_URL}/api/v1/checkins/today",
                headers=api_headers
            )
            if r.status_code == 200:
                data = r.json()
                dcs = data.get('dcs')
                mode = data.get('mode')
                pending = data.get('pending', [])
                
                context = ""
                if dcs:
                    context += f"\n[Shivam's DCS today: {dcs} — Mode: {mode}]"
                if pending:
                    context += f"\n[Pending check-ins: {', '.join(pending)}]"
                return context
    except:
        pass
    return ""

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

async def route(text: str) -> dict:
    content = await call_groq([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": text}
    ], model="llama-3.1-8b-instant")  # 8b for routing — fast
    try:
        return json.loads(content)
    except:
        return {"action": "converse"}

async def converse(text: str, extra_context: str = "") -> str:
    system = CONVERSE_PROMPT + extra_context
    return await call_groq([
        {"role": "system", "content": system},
        {"role": "user", "content": text}
    ], model="llama-3.3-70b-versatile", temperature=0.6)  # 70b for real conversation

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Locus online — second brain active.\n\n"
        "Talk to me. Search your notes. Capture ideas.\n"
        "Log check-ins and tasks → locusapp.online"
    )

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    try:
        action = await route(text)
    except Exception as e:
        await update.message.reply_text(f"Routing error: {e}")
        return

    a = action.get("action")

    if a == "vault_search":
        query = action.get("query", text)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{API_URL}/api/v1/vault/search",
                params={"q": query},
                headers=api_headers,
                timeout=45
            )
        if r.status_code != 200:
            # Brain unavailable — use Groq to converse about the topic instead
            reply = await converse(f"Shivam asked: '{text}'. The vault search is unavailable. Respond based on what you know about him.")
            await update.message.reply_text(reply)
            return
        
        results = r.json().get("results", [])
        if results and results[0].get("excerpt"):
            await update.message.reply_text(results[0]["excerpt"])
        else:
            # No results — have brain respond conversationally
            reply = await converse(f"Shivam searched for '{query}' in his vault but nothing was found. Respond helpfully.")
            await update.message.reply_text(reply)

    elif a == "capture":
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_URL}/api/v1/captures",
                json={"text": action.get("text", text), "source": "telegram"},
                headers=api_headers,
                timeout=10
            )
        if r.status_code == 200:
            await update.message.reply_text("Captured ✓")
        else:
            await update.message.reply_text("Capture failed — FastAPI may be down.")

    elif a == "redirect_to_pwa":
        await update.message.reply_text(
            "Log that at locusapp.online"
        )

    else:  # converse — uses 70b
        behavioral_ctx = await get_behavioral_context()
        reply = await converse(text, extra_context=behavioral_ctx)
        await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Locus bot v3 started — 70b conversation active.")
    app.run_polling()

if __name__ == "__main__":
    main()
