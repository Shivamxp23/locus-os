from fastapi import APIRouter, Request
from app.config import settings
import httpx

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram — simple, non-blocking handler."""
    try:
        data = await request.json()
        message = data.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        voice = message.get("voice")

        if not chat_id:
            return {"ok": True}

        # Look up user by telegram_chat_id
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import select
        from app.models.models import User
        from datetime import datetime

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with SessionLocal() as db:
            result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
            user = result.scalar_one_or_none()

        await engine.dispose()

        if not user:
            # Reply asking them to link their account
            await _send_message(chat_id, 
                f"Your Telegram is not linked to Locus.\n\nYour Chat ID is: `{chat_id}`\n\nGo to Locus Settings to link it.",
                parse_mode="Markdown"
            )
            return {"ok": True}

        if voice:
            # Handle voice note
            await _send_message(chat_id, "🎙 Transcribing...")
            file_id = voice["file_id"]
            # Get file path from Telegram
            async with httpx.AsyncClient() as client:
                file_resp = await client.get(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile",
                    params={"file_id": file_id}
                )
                file_path = file_resp.json()["result"]["file_path"]
                audio_resp = await client.get(
                    f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
                )
                audio_data = audio_resp.content

            from app.services.voice import transcribe_voice
            transcription = await transcribe_voice(audio_data, "voice.ogg")

            if not transcription:
                await _send_message(chat_id, "Could not transcribe. Please try again.")
                return {"ok": True}

            text = transcription
            await _send_message(chat_id, f"Transcribed: _{transcription}_", parse_mode="Markdown")

        if text and not text.startswith("/"):
            # Queue to Engine 1
            try:
                from app.workers.celery_app import app as celery_app
                celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
                    "event_data": {
                        "type": "telegram_message",
                        "user_id": user.id,
                        "source": "telegram",
                        "content": text,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }, queue="engine1")
            except Exception:
                pass

            await _send_message(chat_id, "✓ Logged")

        elif text == "/start":
            await _send_message(chat_id, f"Welcome to Locus! Your account is linked. Send me any text or voice note to log it.")

    except Exception as e:
        pass

    return {"ok": True}

async def _send_message(chat_id: str, text: str, parse_mode: str = None):
    """Send a message back to the user via Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json=payload
            )
    except Exception:
        pass
