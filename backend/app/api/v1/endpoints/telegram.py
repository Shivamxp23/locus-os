from fastapi import APIRouter, Request
from app.config import settings
from app.engines.e1.dcs import calculate_dcs, Mode
import httpx
import re
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

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
    """Generate contextual response per F-012."""
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

    if text.startswith("/"):
        return None

    return (
        f"\U0001f4dd *Logged:*\n_{text}_\n\n"
        f"Captured to your behavioral stream. "
        f"The system will process this during the next snapshot cycle.\n\n"
        f"_Tip: Start messages with 'log', 'done', 'defer', or 'add task' for smarter responses._"
    )


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram — smart response handler per F-012."""
    try:
        body = await request.body()
        logger.info(f"Webhook raw body: {body.decode('utf-8', errors='replace')}")
        data = await request.json()
        logger.info(f"Webhook received: {data}")
        message = data.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        voice = message.get("voice")
        logger.info(f"Parsed: chat_id={chat_id}, text={text}, voice={voice}")

        if not chat_id:
            return {"ok": True}

        from sqlalchemy.ext.asyncio import (
            create_async_engine,
            AsyncSession,
            async_sessionmaker,
        )
        from sqlalchemy import select
        from app.models.models import User
        from datetime import datetime

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with SessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == chat_id)
            )
            user = result.scalar_one_or_none()
            logger.info(f"User lookup result: {user.display_name if user else 'None'}")

        await engine.dispose()

        if not user:
            logger.info(f"User not linked for chat_id={chat_id}, sending link message")
            await _send_message(
                chat_id,
                f"Your Telegram is not linked to Locus.\n\nYour Chat ID is: `{chat_id}`\n\nGo to Locus Settings to link it.",
                parse_mode="Markdown",
            )
            return {"ok": True}

        if voice:
            await _send_message(chat_id, "\U0001f399\ufe0f Transcribing...")
            file_id = voice["file_id"]
            async with httpx.AsyncClient() as client:
                file_resp = await client.get(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile",
                    params={"file_id": file_id},
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
            await _send_message(
                chat_id,
                f"\u2705 *Voice note transcribed:*\n\n_{transcription}_\n\nSaved to your inbox.",
                parse_mode="Markdown",
            )

        if text == "/start":
            await _send_message(
                chat_id,
                f"Welcome to Locus! \U0001f9e0\n\n"
                f"Your account is linked. Send me any text or voice note to log it.\n\n"
                f"*Quick commands:*\n"
                f"\u2022 `log E M S ST T` \u2014 Morning metrics\n"
                f"\u2022 `done [task]` \u2014 Complete a task\n"
                f"\u2022 `defer [task]` \u2014 Defer a task\n"
                f"\u2022 `add task [name]` \u2014 Create a task\n"
                f"\u2022 `what should i do` \u2014 Get recommendations\n\n"
                f"Your Chat ID: `{chat_id}`",
                parse_mode="Markdown",
            )
        elif text and not text.startswith("/"):
            logger.info(f"Generating smart response for text: {text}")
            response = _generate_smart_response(text)
            logger.info(
                f"Smart response generated: {response[:100] if response else 'None'}"
            )
            if response:
                await _send_message(chat_id, response, parse_mode="Markdown")
            else:
                await _send_message(
                    chat_id,
                    "\u2705 Message logged. The system will process it during the next cycle.",
                )

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)

    return {"ok": True}


async def _send_message(chat_id: str, text: str, parse_mode: str = None):
    """Send a message back to the user via Telegram Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN configured")
        return
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
            else:
                logger.info(f"Telegram message sent to {chat_id}: {resp.json()}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
