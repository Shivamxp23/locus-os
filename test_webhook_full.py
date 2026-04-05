import sys

sys.path.insert(0, "/app")
import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.models.models import User
from app.api.v1.endpoints.telegram import _generate_smart_response


async def test():
    token = "8249321165:AAHOqwRqSMfzBQx5Fbndl1B99WQnUOf_GlI"
    chat_id = "8089688853"
    text = "log 7 6 8 3 5"

    print(f'Testing with chat_id={chat_id}, text="{text}"')

    engine = create_async_engine(
        "postgresql+asyncpg://locus:LocusPostgres2026@postgres:5432/locus", echo=False
    )
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalar_one_or_none()

    await engine.dispose()

    if not user:
        print("ERROR: User not found for this chat_id")
        return

    print(f"Found user: {user.display_name}")

    response = _generate_smart_response(text)
    print(f"Generated response: {response}")

    payload = {"chat_id": chat_id, "text": response, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage", json=payload
            )
            print(f"Telegram API status: {resp.status_code}")
            print(f"Telegram API body: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")


asyncio.run(test())
