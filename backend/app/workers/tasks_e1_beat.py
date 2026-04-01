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
    "gcal-poll-every-15m": {
        "task": "app.workers.tasks_e1_beat.poll_google_calendar_for_all_users",
        "schedule": crontab(minute="*/15"),
    },
    "backup-daily-3am": {
        "task": "app.workers.tasks_e1_beat.run_backup",
        "schedule": crontab(hour=3, minute=0),
    },
}

@app.task(queue="engine1")
def poll_notion_for_all_users():
    """Poll Notion for changes using the global NOTION_API_KEY (internal integration)."""
    import asyncio
    asyncio.run(_poll_notion())

async def _poll_notion():
    from app.config import settings
    from app.services.notion_service import get_notion_client, ensure_notion_databases
    import redis.asyncio as aioredis
    from datetime import datetime, timedelta

    notion = get_notion_client()
    if not notion:
        return  # No API key configured — skip silently

    r = aioredis.from_url(settings.REDIS_URL)

    try:
        # Ensure databases exist (auto-creates on first run)
        db_ids = await ensure_notion_databases()
        if not db_ids:
            print("[Notion] No databases available, skipping poll", flush=True)
            return

        # Poll each managed database for recent changes
        for db_key, db_id in db_ids.items():
            if not db_id:
                continue

            last_poll_key = f"notion:last_poll:{db_key}"
            last_poll = await r.get(last_poll_key)
            after_time = last_poll.decode() if last_poll else (
                datetime.utcnow() - timedelta(hours=1)
            ).isoformat() + "Z"

            try:
                results = await notion.databases.query(
                    database_id=db_id,
                    sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
                    page_size=20,
                )
            except Exception as e:
                print(f"[Notion] Query error for {db_key}: {e}", flush=True)
                continue

            for page in results.get("results", []):
                page_id = page["id"]
                last_edited = page.get("last_edited_time", "")

                cache_key = f"notion:last_edit:{db_key}:{page_id}"
                known_edit = await r.get(cache_key)

                if known_edit and known_edit.decode() == last_edited:
                    continue

                # Check if this was created by Locus itself (avoid loops)
                locus_id_prop = page.get("properties", {}).get("Locus ID", {})
                rich_texts = locus_id_prop.get("rich_text", [])
                if rich_texts:
                    # This page was created by Locus — skip to avoid feedback loop
                    await r.set(cache_key, last_edited)
                    continue

                # Extract title
                title = ""
                for prop in page.get("properties", {}).values():
                    if prop.get("type") == "title":
                        title_parts = prop.get("title", [])
                        title = "".join(t.get("plain_text", "") for t in title_parts)
                        break

                # Determine user — for now use default user
                # In multi-user mode, pages would be tagged with user ID
                from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
                from sqlalchemy import select
                from app.models.models import User

                engine = create_async_engine(settings.DATABASE_URL, echo=False)
                S = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with S() as db:
                    result = await db.execute(select(User).where(User.is_active == True).limit(1))
                    user = result.scalar_one_or_none()
                await engine.dispose()

                if not user:
                    continue

                from app.workers.celery_app import app as celery_app
                celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
                    "event_data": {
                        "type": "notion_page_changed",
                        "user_id": user.id,
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


@app.task(queue="engine1")
def poll_google_calendar_for_all_users():
    """Poll Google Calendar for all users with linked tokens."""
    import asyncio
    asyncio.run(_poll_gcal_all())


async def _poll_gcal_all():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.config import settings
    from app.models.models import User

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.google_refresh_token != None, User.is_active == True)
        )
        users = result.scalars().all()

    for user in users:
        poll_google_calendar_for_user.delay(user.id, user.google_access_token, user.google_refresh_token)

    await engine.dispose()


@app.task(queue="engine1")
def poll_google_calendar_for_user(user_id: str, access_token: str, refresh_token: str):
    """Fetch upcoming events and log them as behavioral events."""
    import asyncio
    asyncio.run(_fetch_and_log_gcal_events(user_id, access_token, refresh_token))


async def _fetch_and_log_gcal_events(user_id: str, access_token: str, refresh_token: str):
    from app.services.google_calendar import fetch_upcoming_events, refresh_access_token
    from datetime import datetime

    # Try with existing token, refresh if needed
    events = await fetch_upcoming_events(access_token)
    if not events and refresh_token:
        new_token = await refresh_access_token(refresh_token)
        if new_token:
            access_token = new_token
            events = await fetch_upcoming_events(access_token)

    for event in events:
        title = event.get("summary", "Untitled event")
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
        from app.workers.celery_app import app as celery_app
        celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
            "event_data": {
                "type": "calendar_event",
                "user_id": user_id,
                "source": "google_calendar",
                "content": f"{title} at {start}",
                "created_at": datetime.utcnow().isoformat()
            }
        }, queue="engine1")
