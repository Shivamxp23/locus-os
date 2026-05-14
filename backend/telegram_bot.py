"""
telegram_bot.py — Locus Telegram Bot (System 1 Router)

This is the primary interface between Shivam and Locus. Every single
message passes through the full routing pipeline:

1. Message received
2. → Query Classifier (classify intent + required sources)
3. → Parallel Source Retriever (async fetch from all DBs)
4. → Context Synthesizer (merge + compress to 800-token budget)
5. → LLM Selection (8b-instant vs 70b-versatile based on complexity)
6. → LLM call with synthesized context + system prompt
7. → Response with 👍/👎 feedback buttons

The bot NEVER skips steps 2-4. If context retrieval fails completely,
it tells the user honestly rather than hallucinating.
"""

import os
import json
import logging
import asyncio
from datetime import datetime

import httpx
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

from core.query_classifier import classify_query
from core.source_retriever import parallel_retrieve
from core.context_synthesizer import synthesize_context
from core.hebbian import apply_feedback_signal, increment_traversed_weights
from core.shorthand import SHORTHAND_SCHEMA_PROMPT
from services.vault_chat_logger import log_chat_exchange

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("locus-bot")

TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_ID", "0"))
GROQ_KEY = os.getenv("GROQ_API_KEY")

# ═══════════════════════════════════════════════════════════════
#  SYSTEM PROMPT — This is what makes Locus Locus
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are Locus — Shivam's personal cognitive operating system. You are NOT a generic AI assistant. You are Shivam's second brain.

IDENTITY:
- Shivam is a CS student (B.Tech), filmmaker, and developer. He runs 4 life factions: Health, Leverage (career/money), Craft (technical mastery), Expression (filmmaking/writing).
- He is direct, hates sycophancy, values push-back, and prefers blunt honesty. Never use phrases like "Great question!" or "I'd be happy to help!" — he will lose respect for you instantly.
- He built you (Locus) as his self-hosted personal OS. You run on his Oracle Cloud ARM64 VM.

YOUR BEHAVIOR:
- NEVER answer from your parametric knowledge when personal data exists. You are given context from Shivam's databases below. USE IT.
- If the context says [NO_PERSONAL_DATA], then and ONLY then may you answer from general knowledge, but you MUST state that you're doing so.
- Be specific. Cite data points. "Your mood was 4/10 yesterday" not "you seem stressed lately."
- If you notice something in the data the user didn't ask about but seems important, mention it briefly.
- Match Shivam's communication style: direct, concise, technically precise.
- You can push back on him if you think he's wrong or avoiding something. He respects that.

DATA FORMAT:
""" + SHORTHAND_SCHEMA_PROMPT + """

CONTEXT LAYERS:
- [CONTEXT_META]: metadata about what data sources were queried
- [TEMPORAL]: current time and date context
- [STATE]: Shivam's current psychological/operational state from the inference engine
- [POSTGRES]: recent events, tasks, check-ins (may be in LOCUS_SHORTHAND format)
- [NEO4J]: personality graph data — traits, patterns, avoidances, weighted pathways
- [SEMANTIC]: relevant notes from Obsidian vault and Qdrant vector search
- [WEB]: web search results (only if needed for external knowledge)
- [NO_PERSONAL_DATA]: warning that no personal data was found — answer from general knowledge but state so clearly

Always prioritize personal data context over your training data."""


async def call_groq(
    messages: list,
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.5,
    max_tokens: int = 800
) -> tuple[str, dict]:
    """
    Call Groq API. Returns (response_text, usage_dict).
    """
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, usage


# ═══════════════════════════════════════════════════════════════
#  AUTH DECORATOR
# ═══════════════════════════════════════════════════════════════

def owner_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper


# ═══════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════

@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Locus System 1 Online*\n\n"
        "Every message routes through:\n"
        "1. Intent Classification\n"
        "2. Parallel Data Retrieval (PG + Neo4j + Qdrant + Vault)\n"
        "3. Context Synthesis (800-token budget)\n"
        "4. LLM Response (with your personal data)\n\n"
        "Commands: /debug /status",
        parse_mode="Markdown"
    )


@owner_only
async def cmd_debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show the last query's routing decision and retrieval results."""
    debug_info = ctx.user_data.get("last_debug_info")
    if not debug_info:
        await update.message.reply_text("No debug info available. Send a query first.")
        return

    routing = debug_info.get("routing", {})
    retrieved = debug_info.get("retrieved", {})
    model_used = debug_info.get("model_used", "?")
    tokens = debug_info.get("tokens", {})

    text = "🔍 *Last Query Debug*\n\n"
    text += f"*Intent:* {routing.get('primary_intent', '?')}\n"
    text += f"*Secondary:* {routing.get('secondary_intents', [])}\n"
    text += f"*Confidence:* {routing.get('confidence', '?')}\n"
    text += f"*Scope:* {routing.get('temporal_scope', '?')}\n"
    text += f"*Deep reasoning:* {routing.get('requires_deep_reasoning', False)}\n"
    text += f"*Model:* {model_used}\n"
    text += f"*Tokens:* prompt={tokens.get('prompt_tokens', '?')} completion={tokens.get('completion_tokens', '?')}\n\n"

    text += "*Sources Retrieved:*\n"
    for src, data in retrieved.items():
        if isinstance(data, dict):
            non_empty = sum(1 for v in data.values() if v)
            total_keys = len(data)
            text += f"  • {src}: {non_empty}/{total_keys} fields populated\n"
        elif isinstance(data, list):
            text += f"  • {src}: {len(data)} items\n"
        else:
            text += f"  • {src}: {'has data' if data else 'empty'}\n"

    # Truncate for Telegram
    await update.message.reply_text(text[:4000], parse_mode="Markdown")


@owner_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show current system status — state, token usage, etc."""
    from core.db import redis_get_json, redis_get_int

    state = await redis_get_json("locus:current_state")
    tokens = await redis_get_int("groq_tokens_today")

    text = "📊 *Locus System Status*\n\n"
    text += f"*Groq tokens today:* {tokens}\n"

    if state:
        psych = state.get("psychological_state", {})
        ops = state.get("operational_state", {})
        text += f"\n*Current State:*\n"
        text += f"  Mood: {psych.get('mood_value', '?')}/10 ({psych.get('mood_trend', '?')})\n"
        text += f"  Energy: {psych.get('energy_level', '?')}/10 ({psych.get('energy_trend', '?')})\n"
        text += f"  Momentum: {ops.get('momentum', '?')}\n"
        text += f"  Done today: {ops.get('tasks_completed_today', '?')}\n"
        text += f"  Deferred today: {ops.get('tasks_deferred_today', '?')}\n"

        alerts = state.get("behavioral_alerts", [])
        if alerts:
            text += f"\n*Alerts:*\n"
            for a in alerts[:3]:
                text += f"  ⚠️ [{a.get('severity', '?')}] {a.get('description', '')[:80]}\n"

        cause = state.get("inferred_cause_chain", "")
        if cause:
            text += f"\n*Inferred cause chain:*\n{cause[:500]}\n"
    else:
        text += "\n_No state inferred yet. Send a message to trigger inference._"

    await update.message.reply_text(text[:4000], parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════
#  FEEDBACK HANDLER (👍/👎)
# ═══════════════════════════════════════════════════════════════

@owner_only
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("fb_"):
        parts = data.split("_", 3)
        if len(parts) >= 3:
            action = parts[1]  # "up" or "down"
            interaction_id = parts[2] if len(parts) > 2 else "unknown"

            signal = "thumbs_up" if action == "up" else "thumbs_down"
            pathways = ctx.user_data.get(f"pathways_{interaction_id}", [])

            # Apply Hebbian feedback
            await apply_feedback_signal(interaction_id, signal, pathways)

            emoji = "👍" if action == "up" else "👎"
            try:
                new_text = query.message.text + f"\n\n_{emoji} Feedback recorded_"
                await query.edit_message_text(text=new_text)
            except Exception:
                pass  # Message might be too old to edit


# ═══════════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER — The Full Pipeline
# ═══════════════════════════════════════════════════════════════

@owner_only
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    The core message handler. Every message goes through the full
    System 1 pipeline. NO EXCEPTIONS.
    """
    text = update.message.text
    if not text:
        return

    thinking_msg = await update.message.reply_text("🧠 Routing...")

    try:
        # ── Quick actions (captures) ──
        if text.lower().startswith(("note:", "capture:")):
            try:
                from core.db import pg_execute
                await pg_execute("""
                    INSERT INTO captures (user_id, text, source)
                    VALUES ('shivam', $1, 'telegram')
                """, text)
                await thinking_msg.edit_text("✅ Captured & saved")
                return
            except Exception:
                pass

        # ══════════════════════════════════════════════
        # STEP 1: Query Classification (~50 tokens, <500ms)
        # ══════════════════════════════════════════════
        routing_info = await classify_query(text)
        primary = routing_info.get("primary_intent", "?")
        await thinking_msg.edit_text(
            f"🧠 Routing...\n├ Intent: {primary}\n├ Fetching from: {', '.join(routing_info.get('sources_required', []))}"
        )

        # ══════════════════════════════════════════════
        # STEP 2: Parallel Source Retrieval (all sources async)
        # ══════════════════════════════════════════════
        retrieved_data = await parallel_retrieve(text, routing_info)
        sources_with_data = [k for k, v in retrieved_data.items() if v]
        await thinking_msg.edit_text(
            f"🧠 Routing...\n├ Intent: {primary}\n├ Sources: {', '.join(sources_with_data)}\n├ Synthesizing..."
        )

        # ── Hebbian: increment traversal weights ──
        neo4j_data = retrieved_data.get("neo4j", {})
        if isinstance(neo4j_data, dict) and neo4j_data.get("pathways"):
            asyncio.create_task(
                increment_traversed_weights(neo4j_data["pathways"])
            )

        # ══════════════════════════════════════════════
        # STEP 3: Context Synthesis (merge + compress)
        # ══════════════════════════════════════════════
        context_block = synthesize_context(retrieved_data, routing_info)

        # HARD CHECK: Never skip context
        if context_block is None:
            await thinking_msg.edit_text(
                "⚠️ I couldn't retrieve your data right now. "
                "All data sources returned errors. Please try again."
            )
            return

        # ══════════════════════════════════════════════
        # STEP 4: LLM Selection
        # ══════════════════════════════════════════════
        requires_deep = routing_info.get("requires_deep_reasoning", False)
        model = "llama-3.1-8b-instant"
        if requires_deep or primary in ("INFERENCE_REQUEST", "SYNTHESIS"):
            model = "llama-3.3-70b-versatile"

        await thinking_msg.edit_text(
            f"🧠 Routing...\n├ Intent: {primary}\n├ Sources: {', '.join(sources_with_data)}\n├ Context ready\n└ Generating ({model.split('-')[1] if '-' in model else model})..."
        )

        # ══════════════════════════════════════════════
        # STEP 5: LLM Call with Full Context
        # ══════════════════════════════════════════════
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context_block}\n\n---\nShivam says: {text}"},
        ]

        reply, usage = await call_groq(messages, model=model, temperature=0.5)

        # Track token usage
        try:
            from core.db import redis_incr
            total_tokens = usage.get("total_tokens", 0)
            await redis_incr("groq_tokens_today", total_tokens)
        except Exception:
            pass

        # ══════════════════════════════════════════════
        # STEP 6: Send Response with Feedback Buttons
        # ══════════════════════════════════════════════
        interaction_id = f"msg_{update.message.message_id}"

        # Store pathways for Hebbian feedback
        if isinstance(neo4j_data, dict):
            ctx.user_data[f"pathways_{interaction_id}"] = neo4j_data.get("pathways", [])

        # Store debug info
        ctx.user_data["last_debug_info"] = {
            "routing": routing_info,
            "retrieved": retrieved_data,
            "model_used": model,
            "tokens": usage,
        }

        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f"fb_up_{interaction_id}"),
                InlineKeyboardButton("👎", callback_data=f"fb_down_{interaction_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await thinking_msg.delete()
        # Split long replies
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                chunk = reply[i:i + 4000]
                if i + 4000 >= len(reply):
                    await update.message.reply_text(chunk, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(reply, reply_markup=reply_markup)

        # ── Log chat to vault as .md ──
        asyncio.create_task(_background_chat_log(
            text, reply, model, primary
        ))

        # ── Background: trigger state inference on every message ──
        asyncio.create_task(_background_state_update(text))

    except Exception as e:
        log.error(f"Message handler error: {e}", exc_info=True)
        try:
            await thinking_msg.edit_text(f"⚠️ Error: {str(e)[:200]}")
        except Exception:
            pass


async def _background_state_update(user_message: str):
    """Trigger state inference in background after each message."""
    try:
        from core.state_engine import infer_current_state
        await infer_current_state(trigger_event={
            "type": "telegram_message",
            "content": user_message[:200],
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        log.warning(f"Background state update failed: {e}")


async def _background_chat_log(
    user_message: str, bot_reply: str, model: str, intent: str
):
    """Log the chat exchange to vault as a daily .md file."""
    try:
        log_chat_exchange(
            user_message=user_message,
            bot_reply=bot_reply,
            model_used=model,
            intent=intent,
        )
    except Exception as e:
        log.warning(f"Chat log to vault failed: {e}")


# ═══════════════════════════════════════════════════════════════
#  BOT INITIALIZATION
# ═══════════════════════════════════════════════════════════════

def main():
    if not TOKEN:
        log.error("TELEGRAM_TOKEN is not set.")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("debug", cmd_debug))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info("Locus bot v7 (Full System 1 Router + Hebbian) started.")
    app.run_polling()


if __name__ == "__main__":
    main()
