import os
import json
import logging
import asyncio
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sys

from core.query_classifier import classify_query
from core.source_retriever import parallel_retrieve
from core.context_synthesizer import synthesize_context

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("locus-bot")

TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

api_headers = {"X-Service-Token": SERVICE_TOKEN}

async def call_groq(messages: list, model: str = "llama-3.1-8b-instant", temperature: float = 0.5) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": model, "messages": messages, "temperature": temperature}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Locus System 1 Online*\n\n"
        "Routing philosophy: 'Before answering, understand what kind of question this is, what data sources are relevant, and retrieve from all of them in parallel. Never answer from parametric knowledge alone if personal data exists.'\n\n"
        "Commands: /debug",
        parse_mode="Markdown"
    )

@owner_only
async def cmd_debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    debug_info = ctx.user_data.get("last_debug_info")
    if not debug_info:
        await update.message.reply_text("No debug info available for the last query.")
        return
        
    text = "🔍 *Last Query Debug*\n\n"
    text += f"*Routing Decision:*\n```json\n{json.dumps(debug_info['routing'], indent=2)}\n```\n"
    text += f"*Sources Retrieved:*\n"
    for src, data in debug_info['retrieved'].items():
        size = len(json.dumps(data)) if data else 0
        text += f"- {src}: {size} bytes\n"
        
    await update.message.reply_text(text[:4000], parse_mode="Markdown")

async def record_feedback(interaction_id: str, is_upvote: bool, pathways: list):
    """Sends feedback to backend to apply Hebbian weighting."""
    signal = "thumbs_up" if is_upvote else "thumbs_down"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{API_URL}/api/v1/context/reward",
                json={"interaction_id": interaction_id, "signal_type": signal, "pathways": pathways},
                headers=api_headers,
                timeout=5
            )
    except Exception as e:
        log.warning(f"Failed to record feedback: {e}")

@owner_only
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("fb_"):
        parts = data.split("_")
        action = parts[1] # up or down
        interaction_id = parts[2] if len(parts) > 2 else "unknown"
        
        pathways = ctx.user_data.get(f"pathways_{interaction_id}", [])
        await record_feedback(interaction_id, action == "up", pathways)
        
        new_text = query.message.text + f"\n\n[Feedback received: {'👍' if action == 'up' else '👎'}]"
        await query.edit_message_text(text=new_text)

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    thinking_msg = await update.message.reply_text("🧠 Routing query...")
    
    try:
        if text.lower().startswith("note:") or text.lower().startswith("capture:"):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        f"{API_URL}/api/v1/captures",
                        json={"text": text, "source": "telegram"},
                        headers=api_headers
                    )
                if r.status_code == 200:
                    await thinking_msg.edit_text("✅ Captured & indexed into vault")
                    return
            except Exception:
                pass

        if text.lower() == "log my mood":
             await thinking_msg.edit_text("📱 Log that at *locusapp.online*", parse_mode="Markdown")
             return

        routing_info = await classify_query(text)
        await thinking_msg.edit_text(f"🧠 Routing query...\n├ Intents: {routing_info.get('primary_intent')}\n├ Fetching sources in parallel...")
        
        retrieved_data = await parallel_retrieve(text, routing_info)
        await thinking_msg.edit_text(f"🧠 Routing query...\n├ Intents: {routing_info.get('primary_intent')}\n├ Sources retrieved\n├ Synthesizing context...")
        
        context_block = synthesize_context(retrieved_data, routing_info)
        
        if not context_block:
            await thinking_msg.edit_text("⚠️ I couldn't retrieve your data right now, please try again.")
            return

        ctx.user_data["last_debug_info"] = {
            "routing": routing_info,
            "retrieved": retrieved_data
        }
        
        requires_deep = routing_info.get("requires_deep_reasoning", False)
        primary_intent = routing_info.get("primary_intent")
        
        model = "llama-3.1-8b-instant"
        if requires_deep or primary_intent in ["INFERENCE_REQUEST", "SYNTHESIS"]:
            model = "llama-3.3-70b-versatile"
            
        await thinking_msg.edit_text(f"🧠 Routing query...\n├ Intents: {routing_info.get('primary_intent')}\n├ Sources retrieved\n├ Context synthesized\n└ Generating response ({model})...")
        
        prompt = f"System Context:\n{context_block}\n\nUser: {text}"
        reply = await call_groq([{"role": "user", "content": prompt}], model=model)
        
        interaction_id = f"msg_{update.message.message_id}"
        
        neo4j_data = retrieved_data.get("neo4j", {})
        if isinstance(neo4j_data, dict):
            ctx.user_data[f"pathways_{interaction_id}"] = neo4j_data.get("pathways", [])
        
        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f"fb_up_{interaction_id}"),
                InlineKeyboardButton("👎", callback_data=f"fb_down_{interaction_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await thinking_msg.delete()
        await update.message.reply_text(reply, reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"process_text error: {e}")
        await thinking_msg.edit_text(f"⚠️ Error processing query: {e}")

def main():
    if not TOKEN:
        log.error("TELEGRAM_TOKEN is not set.")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("debug", cmd_debug))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    log.info("Locus bot v6 (System 1 Router) started.")
    app.run_polling()

if __name__ == "__main__":
    main()
