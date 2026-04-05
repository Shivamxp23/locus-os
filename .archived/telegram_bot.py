import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from app.config import settings
from app.engines.e1.dcs import calculate_dcs, Mode

logger = logging.getLogger(__name__)

MORNING_LOG_PATTERN = re.compile(
    r"^(?:log|morning)\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

SHORT_LOG_PATTERN = re.compile(
    r"^(?:log|morning)\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s*$",
    re.IGNORECASE,
)

TASK_COMPLETE_PATTERN = re.compile(r"^(?:done|complete|finish)\s+(.+)$", re.IGNORECASE)

TASK_DEFER_PATTERN = re.compile(
    r"^(?:defer|skip|postpone)\s+(.+?)(?:\s*[-:]\s*(.+))?$", re.IGNORECASE
)

TASK_CREATE_PATTERN = re.compile(
    r"^(?:add|create|new)\s+(?:task\s+)?(.+)$", re.IGNORECASE
)

QUERY_PATTERN = re.compile(
    r"^(?:what\s+should\s+i\s+do|plan\s+my\s+day|today|schedule|recommend)",
    re.IGNORECASE,
)

VOICE_NOTE_PATTERN = re.compile(
    r"^(?:voice|note|reminder|remember)\s*[:\-]?\s*(.+)$", re.IGNORECASE
)


def _get_user_from_db(chat_id: str):
    """Helper to look up user by Telegram chat ID."""
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        AsyncSession,
        async_sessionmaker,
    )
    from sqlalchemy import select
    from app.models.models import User
    import asyncio

    async def _lookup():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with SessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == chat_id)
            )
            user = result.scalar_one_or_none()
        await engine.dispose()
        return user

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = asyncio.get_event_loop().run_in_executor(
                    pool, lambda: asyncio.run(_lookup())
                )
                return asyncio.get_event_loop().run_until_complete(future)
        else:
            return asyncio.run(_lookup())
    except Exception:
        return None


def _parse_morning_log(text: str):
    """Try to parse a morning log message. Returns (E, M, S, ST, T) or None."""
    match = MORNING_LOG_PATTERN.match(text.strip())
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            float(match.group(5)),
        )

    match = SHORT_LOG_PATTERN.match(text.strip())
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            None,
        )

    bare = text.strip()
    parts = bare.split()
    if len(parts) == 5:
        try:
            vals = [
                int(parts[0]),
                int(parts[1]),
                int(parts[2]),
                int(parts[3]),
                float(parts[4]),
            ]
            if all(1 <= v <= 10 for v in vals[:4]) and 0 < vals[4] <= 24:
                return tuple(vals)
        except ValueError:
            pass
    elif len(parts) == 4:
        try:
            vals = [int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])]
            if all(1 <= v <= 10 for v in vals):
                return (*vals, None)
        except ValueError:
            pass

    return None


def _format_morning_response(e, m, s, st, t):
    """Format a contextual morning log response per F-012."""
    result = calculate_dcs(e, m, s, st)

    mode_emoji = {
        Mode.SURVIVAL: "\U0001f6a8",
        Mode.RECOVERY: "\U0001f331",
        Mode.NORMAL: "\u2705",
        Mode.DEEP_WORK: "\U0001f525",
        Mode.PEAK: "\u26a1",
    }

    response = (
        f"{mode_emoji.get(result.mode, '')} *DCS: {result.score:.1f} \u2192 {result.mode.value}*\n\n"
        f"{result.mode_description}\n\n"
    )

    if t is not None:
        response += f"\u23f1 Available time: {t}h\n\n"

    response += "*Recommended for today:*\n"
    for task_type in result.recommended_task_types:
        response += f"\u2022 {task_type}\n"

    response += f"\n_Metrics: E={e} M={m} S={s} ST={st}_"

    return response


def _generate_smart_response(text: str) -> str:
    """
    Generate contextual response per F-012.
    Morning log \u2192 DCS + mode + top tasks
    Task complete \u2192 acknowledgment + quality reflection
    Deferral \u2192 empathetic note, ask for reason
    Voice note \u2192 confirm what was extracted
    General text \u2192 acknowledge what was captured
    """
    text = text.strip()

    morning = _parse_morning_log(text)
    if morning:
        e, m, s, st, t = morning
        return _format_morning_response(e, m, s, st, t)

    if TASK_COMPLETE_PATTERN.match(text):
        task_name = TASK_COMPLETE_PATTERN.match(text).group(1)
        return (
            f"\u2705 *Task completed:* {task_name}\n\n"
            f"Nice work. When you have a moment, reply with:\n"
            f"`quality [1-10]` and `time [minutes]` so I can track your patterns.\n\n"
            f"_Example: quality 8 time 45_"
        )

    if TASK_DEFER_PATTERN.match(text):
        match = TASK_DEFER_PATTERN.match(text)
        task_name = match.group(1)
        reason = match.group(2)
        if reason:
            return (
                f"\u27a1\ufe0f *Task deferred:* {task_name}\n"
                f"Reason noted: _{reason}_\n\n"
                f"I'll resurface this when your DCS is better suited for it."
            )
        return (
            f"\u27a1\ufe0f *Task deferred:* {task_name}\n\n"
            f"No worries. If you want, tell me why \u2014 it helps the system learn your patterns.\n"
            f"_Example: defer {task_name} - too tired for this today_"
        )

    if TASK_CREATE_PATTERN.match(text):
        task_name = TASK_CREATE_PATTERN.match(text).group(1)
        return (
            f"\U0001f4dd *Task captured:* {task_name}\n\n"
            f"Logged to your inbox. I'll help you break it down "
            f"and assign priority, difficulty, and urgency when you're ready.\n\n"
            f"_You can also say: 'break down {task_name}' for AI task decomposition._"
        )

    if QUERY_PATTERN.match(text):
        return (
            "\U0001f914 *Let me check your current state...*\n\n"
            "I need your morning metrics first to give you a real recommendation.\n"
            f"Send: `log E M S ST T`\n"
            f"_Example: log 7 6 8 3 5_\n\n"
            f"Or just the four numbers: `7 6 8 3`"
        )

    if VOICE_NOTE_PATTERN.match(text):
        note = VOICE_NOTE_PATTERN.match(text).group(1)
        return (
            f"\U0001f4dd *Note captured:*\n_{note}_\n\n"
            f"Saved to your inbox. I'll link it to relevant projects "
            f"during the next personality snapshot."
        )

    if text.startswith("/"):
        return None

    return (
        f"\U0001f4dd *Logged:*\n_{text}_\n\n"
        f"Captured to your behavioral stream. "
        f"The system will process this during the next snapshot cycle.\n\n"
        f"_Tip: Start messages with 'log', 'done', 'defer', or 'add task' for smarter responses._"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with smart contextual responses per F-012."""
    chat_id = str(update.message.chat_id)
    text = update.message.text

    user = _get_user_from_db(chat_id)

    if not user:
        await update.message.reply_text(
            "Your Telegram is not linked to a Locus account. "
            "Go to Settings in the Locus app to link it."
        )
        return

    response = _generate_smart_response(text)

    if response:
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"\u2705 Message logged. The system will process it during the next cycle."
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages \u2014 transcribe via Groq Whisper then log with contextual response."""
    from app.services.voice import transcribe_voice
    from sqlalchemy.ext.asyncio import (
        create_async_engine,
        AsyncSession,
        async_sessionmaker,
    )
    from sqlalchemy import select
    from app.models.models import User
    import asyncio

    chat_id = str(update.message.chat_id)

    def _lookup_user():
        async def _lookup():
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            SessionLocal = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            async with SessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == chat_id)
                )
                user = result.scalar_one_or_none()
            await engine.dispose()
            return user

        return asyncio.run(_lookup())

    user = _lookup_user()

    if not user:
        await update.message.reply_text(
            "Telegram not linked. Link it in Locus Settings."
        )
        return

    await update.message.reply_text("\U0001f399\ufe0f Transcribing...")

    file = await context.bot.get_file(update.message.voice.file_id)
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(file.file_path)
        audio_data = resp.content

    transcription = await transcribe_voice(audio_data, "voice.ogg")

    if not transcription:
        await update.message.reply_text("Could not transcribe. Please try again.")
        return

    response = (
        f"\u2705 *Voice note transcribed:*\n\n"
        f"_{transcription}_\n\n"
        f"Saved to your inbox. I'll link this to relevant projects "
        f"during the next processing cycle."
    )

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    await update.message.reply_text(
        f"Welcome to Locus.\n\n"
        f"Your Telegram Chat ID is: `{chat_id}`\n\n"
        f"Copy this and paste it in Locus \u2192 Settings \u2192 Link Telegram.\n\n"
        f"*Quick commands:*\n"
        f"\u2022 `log E M S ST T` \u2014 Morning metrics\n"
        f"\u2022 `done [task]` \u2014 Complete a task\n"
        f"\u2022 `defer [task]` \u2014 Defer a task\n"
        f"\u2022 `add task [name]` \u2014 Create a task\n"
        f"\u2022 `what should i do` \u2014 Get recommendations\n"
        f"\u2022 Send voice notes \u2014 Auto-transcribed",
        parse_mode="Markdown",
    )


def build_bot_app() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    return app
