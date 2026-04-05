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
        result = await db.execute(
            select(User).where(User.telegram_chat_id == "8089688853")
        )
        users = result.scalars().all()
        print(f"Found {len(users)} users with chat_id 8089688853")
        for u in users:
            print(f"  ID: {u.id}, Name: {u.display_name}, Created: {u.created_at}")
        if len(users) > 1:
            print(f"\nDeleting duplicate: {users[0].id} ({users[0].display_name})")
            await db.delete(users[0])
            await db.commit()
            print("Deleted. Now checking again...")
            result2 = await db.execute(
                select(User).where(User.telegram_chat_id == "8089688853")
            )
            users2 = result2.scalars().all()
            print(f"Now {len(users2)} user(s) remain")
            for u in users2:
                print(f"  ID: {u.id}, Name: {u.display_name}")
    await engine.dispose()


asyncio.run(main())
