import sys

sys.path.insert(0, "/app")
import asyncio
import httpx
import re
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MORNING_LOG_PATTERN = re.compile(
    r"^(?:log|morning)\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)


def _parse_morning_log(text):
    match = MORNING_LOG_PATTERN.match(text.strip())
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            float(match.group(5)),
        )
    return None


def _format_morning_response(e, m, s, st, t):
    from app.engines.e1.dcs import calculate_dcs, Mode

    result = calculate_dcs(e, m, s, st)
    mode_emoji = {
        Mode.SURVIVAL: "🚨",
        Mode.RECOVERY: "🌱",
        Mode.NORMAL: "✅",
        Mode.DEEP_WORK: "🔥",
        Mode.PEAK: "⚡",
    }
    response = f"{mode_emoji.get(result.mode, '')} *DCS: {result.score:.1f} → {result.mode.value}*\n\n"
    response += f"{result.mode_description}\n\n"
    if t is not None:
        response += f"⏱ Available time: {t}h\n\n"
    response += "*Recommended for today:*\n"
    for task_type in result.recommended_task_types:
        response += f"• {task_type}\n"
    response += f"\n_Metrics: E={e} M={m} S={s} ST={st}_"
    return response


async def send_message(chat_id, text):
    token = "8249321165:AAHOqwRqSMfzBQx5Fbndl1B99WQnUOf_GlI"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    print(f"Sending to Telegram API: chat_id={chat_id}")
    print(f"Payload text length: {len(text)}")
    print(f"First 100 chars: {text[:100]}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage", json=payload
            )
            print(f"Telegram API status: {resp.status_code}")
            print(f"Telegram API response: {resp.text[:500]}")
    except Exception as e:
        print(f"Exception: {e}")


async def main():
    text = "log 7 6 8 3 5"
    chat_id = "8089688853"

    parsed = _parse_morning_log(text)
    print(f"Parsed: {parsed}")

    if parsed:
        e, m, s, st, t = parsed
        response = _format_morning_response(e, m, s, st, t)
        print(f"Response generated, length: {len(response)}")
        await send_message(chat_id, response)
    else:
        print("Failed to parse")


asyncio.run(main())
