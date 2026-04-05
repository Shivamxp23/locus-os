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
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            tg = u.telegram_chat_id
            print(f"ID: {u.id}")
            print(f"Display: {u.display_name}")
            print(f"Telegram: {repr(tg)} type={type(tg).__name__}")
            if tg:
                print(f"Match 8089688853: {str(tg) == '8089688853'}")
            print("---")
    await engine.dispose()


asyncio.run(main())
