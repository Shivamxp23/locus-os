import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.config import settings

logger = logging.getLogger(__name__)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — log as behavioral event via Engine 1."""
    from app.workers.celery_app import app as celery_app
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.models import User
    from datetime import datetime

    chat_id = str(update.message.chat_id)
    text = update.message.text

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalar_one_or_none()

    await engine.dispose()

    if not user:
        await update.message.reply_text(
            "Your Telegram is not linked to a Locus account. "
            "Go to Settings in the Locus app to link it."
        )
        return

    celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
        "event_data": {
            "type": "telegram_message",
            "user_id": user.id,
            "source": "telegram",
            "content": text,
            "created_at": datetime.utcnow().isoformat()
        }
    }, queue="engine1")

    await update.message.reply_text(f"Logged ✓")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe via Groq Whisper then log."""
    from app.services.voice import transcribe_voice
    from app.workers.celery_app import app as celery_app
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.models import User
    from datetime import datetime

    chat_id = str(update.message.chat_id)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalar_one_or_none()
    await engine.dispose()

    if not user:
        await update.message.reply_text("Telegram not linked. Link it in Locus Settings.")
        return

    await update.message.reply_text("Transcribing...")

    file = await context.bot.get_file(update.message.voice.file_id)
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(file.file_path)
        audio_data = resp.content

    transcription = await transcribe_voice(audio_data, "voice.ogg")

    if not transcription:
        await update.message.reply_text("Could not transcribe. Please try again.")
        return

    celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
        "event_data": {
            "type": "voice_note",
            "user_id": user.id,
            "source": "telegram",
            "content": transcription,
            "created_at": datetime.utcnow().isoformat()
        }
    }, queue="engine1")

    await update.message.reply_text(f"Transcribed & logged:\n\n_{transcription}_", parse_mode="Markdown")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    await update.message.reply_text(
        f"Welcome to Locus.\n\n"
        f"Your Telegram Chat ID is: `{chat_id}`\n\n"
        f"Copy this and paste it in Locus → Settings → Link Telegram.",
        parse_mode="Markdown"
    )

def build_bot_app() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    return app
