import sys

sys.path.insert(0, "/app")
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.models.models import User


async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://locus:LocusPostgres2026@postgres:5432/locus", echo=False
    )
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id.isnot(None)))
        users = result.scalars().all()
        for u in users:
            print(f"Display: {u.display_name}")
            print(
                f"telegram_chat_id: repr={repr(u.telegram_chat_id)} type={type(u.telegram_chat_id)}"
            )
            match_val = "8089688853"
            print(f"Match with 8089688853: {u.telegram_chat_id == match_val}")
            print(f"Match with str(8089688853): {str(u.telegram_chat_id) == match_val}")
            print("---")
    await engine.dispose()


asyncio.run(main())
