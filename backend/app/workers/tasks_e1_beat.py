"""
Celery Beat scheduled tasks for Engine 1.
These run on a schedule, not triggered by user actions.
"""
from app.workers.celery_app import app
from celery.schedules import crontab

# Register beat schedule
app.conf.beat_schedule = {
    "notion-poll-every-60s": {
        "task": "app.workers.tasks_e1_beat.poll_notion_for_all_users",
        "schedule": 60.0,
    },
    "backup-daily-3am": {
        "task": "app.workers.tasks_e1_beat.run_backup",
        "schedule": crontab(hour=3, minute=0),
    },
}

@app.task(queue="engine1")
def poll_notion_for_all_users():
    """Poll Notion for all users with a linked Notion token."""
    import asyncio
    asyncio.run(_poll_notion())

async def _poll_notion():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.config import settings
    from app.models.models import User

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.notion_access_token != None, User.is_active == True)
        )
        users = result.scalars().all()

    for user in users:
        poll_notion_for_user.delay(user.id, user.notion_access_token)

    await engine.dispose()

@app.task(queue="engine1")
def poll_notion_for_user(user_id: str, notion_token: str):
    """Poll Notion for a single user and publish changes to Engine 1."""
    import asyncio
    asyncio.run(_poll_user_notion(user_id, notion_token))

async def _poll_user_notion(user_id: str, notion_token: str):
    from notion_client import AsyncClient
    from app.config import settings
    import redis.asyncio as aioredis
    from datetime import datetime, timedelta

    notion = AsyncClient(auth=notion_token)
    r = aioredis.from_url(settings.REDIS_URL)

    try:
        # Get last poll time from Redis
        last_poll_key = f"notion:last_poll:{user_id}"
        last_poll = await r.get(last_poll_key)
        after_time = last_poll.decode() if last_poll else (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat() + "Z"

        # Search for recently edited pages
        results = await notion.search(
            filter={"property": "object", "value": "page"},
            sort={"direction": "descending", "timestamp": "last_edited_time"}
        )

        for page in results.get("results", []):
            page_id = page["id"]
            last_edited = page.get("last_edited_time", "")

            # Check if we've seen this version
            cache_key = f"notion:last_edit:{user_id}:{page_id}"
            known_edit = await r.get(cache_key)

            if known_edit and known_edit.decode() == last_edited:
                continue

            # Something changed — publish to Engine 1
            title = ""
            if page.get("properties"):
                for prop in page["properties"].values():
                    if prop.get("type") == "title":
                        title_parts = prop.get("title", [])
                        title = "".join([t.get("plain_text", "") for t in title_parts])
                        break

            from app.workers.celery_app import app as celery_app
            celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
                "event_data": {
                    "type": "notion_page_changed",
                    "user_id": user_id,
                    "source": "notion",
                    "content": title or "Notion page updated",
                    "notion_page_id": page_id,
                    "created_at": datetime.utcnow().isoformat()
                }
            }, queue="engine1")

            await r.set(cache_key, last_edited)

        await r.set(last_poll_key, datetime.utcnow().isoformat() + "Z")

    finally:
        await r.aclose()

@app.task(queue="engine1")
def run_backup():
    import subprocess
    subprocess.run(["/opt/locus/infra/scripts/backup.sh"], check=False)
