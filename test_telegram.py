import sys

sys.path.insert(0, "/app")
import asyncio
import httpx


async def test():
    token = "8249321165:AAHOqwRqSMfzBQx5Fbndl1B99WQnUOf_GlI"
    chat_id = "8089688853"

    response_text = (
        "✅ *DCS: 5.9 → NORMAL*\n\n"
        "Standard operating. A full, balanced day is possible.\n\n"
        "⏱ Available time: 5.0h\n\n"
        "*Recommended for today:*\n"
        "• Difficulty ≤ 7 allowed\n"
        "• Balance across at least 2 factions\n"
        "• 3-4 tasks outside non-negotiables\n\n"
        "_Metrics: E=7 M=6 S=8 ST=3_"
    )

    payload = {"chat_id": chat_id, "text": response_text, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage", json=payload
            )
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")


asyncio.run(test())
