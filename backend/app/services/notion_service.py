"""
Notion service — internal integration, auto-provisioning databases.
Uses a single workspace-level NOTION_API_KEY (internal integration).
On first run, auto-creates "Locus Tasks" and "Locus Logs" databases
in the workspace and caches their IDs in Redis.
"""
import logging
from typing import Optional
from notion_client import AsyncClient
from app.config import settings

logger = logging.getLogger("locus.notion")

# ──────────────────────────────────────────────
# Client factory
# ──────────────────────────────────────────────

def get_notion_client() -> Optional[AsyncClient]:
    """Return an async Notion client using the global API key, or None."""
    if not settings.NOTION_API_KEY:
        return None
    return AsyncClient(auth=settings.NOTION_API_KEY)


# ──────────────────────────────────────────────
# Auto-provision databases
# ──────────────────────────────────────────────

# Schema for the Tasks database
TASKS_DB_SCHEMA = {
    "Task": {"title": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "pending", "color": "default"},
                {"name": "in_progress", "color": "blue"},
                {"name": "done", "color": "green"},
                {"name": "deferred", "color": "yellow"},
            ]
        }
    },
    "Priority": {
        "select": {
            "options": [
                {"name": "high", "color": "red"},
                {"name": "medium", "color": "orange"},
                {"name": "low", "color": "gray"},
            ]
        }
    },
    "Source": {
        "select": {
            "options": [
                {"name": "telegram", "color": "blue"},
                {"name": "pwa", "color": "purple"},
                {"name": "voice", "color": "green"},
                {"name": "calendar", "color": "yellow"},
            ]
        }
    },
    "Due Date": {"date": {}},
    "Energy": {
        "select": {
            "options": [
                {"name": "deep", "color": "red"},
                {"name": "light", "color": "green"},
                {"name": "admin", "color": "gray"},
            ]
        }
    },
    "Locus ID": {"rich_text": {}},
}

# Schema for the Logs/Notes database
LOGS_DB_SCHEMA = {
    "Title": {"title": {}},
    "Type": {
        "select": {
            "options": [
                {"name": "thought", "color": "blue"},
                {"name": "voice_note", "color": "green"},
                {"name": "calendar_event", "color": "yellow"},
                {"name": "notion_change", "color": "purple"},
                {"name": "reflection", "color": "pink"},
            ]
        }
    },
    "Source": {
        "select": {
            "options": [
                {"name": "telegram", "color": "blue"},
                {"name": "google_calendar", "color": "yellow"},
                {"name": "notion", "color": "default"},
                {"name": "pwa", "color": "purple"},
            ]
        }
    },
    "Mood": {"number": {"format": "number"}},
    "Tags": {"multi_select": {"options": []}},
    "Logged At": {"date": {}},
    "Locus ID": {"rich_text": {}},
}


async def _find_existing_db(notion: AsyncClient, title_prefix: str) -> Optional[str]:
    """Search for an existing Locus-managed database by title."""
    try:
        results = await notion.search(
            query=title_prefix,
            filter={"property": "object", "value": "database"},
        )
        for db in results.get("results", []):
            db_title = ""
            for t in db.get("title", []):
                db_title += t.get("plain_text", "")
            if db_title.strip() == title_prefix:
                return db["id"]
    except Exception as e:
        logger.warning(f"Notion search error: {e}")
    return None


async def _create_database(
    notion: AsyncClient,
    parent_page_id: str,
    title: str,
    properties: dict,
) -> str:
    """Create a Notion database and return its ID."""
    db = await notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": title}}],
        properties=properties,
    )
    return db["id"]


async def _find_or_create_parent_page(notion: AsyncClient) -> str:
    """
    Find or create a top-level 'Locus OS' page that will be the parent
    for auto-created databases.
    """
    # Search for existing Locus OS page
    results = await notion.search(
        query="Locus OS",
        filter={"property": "object", "value": "page"},
    )
    for page in results.get("results", []):
        # Check title matches
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_parts = prop.get("title", [])
                full_title = "".join(t.get("plain_text", "") for t in title_parts)
                if full_title.strip() == "Locus OS":
                    return page["id"]

    # Not found — create it as a top-level page
    page = await notion.pages.create(
        parent={"type": "workspace", "workspace": True},
        properties={
            "title": [{"type": "text", "text": {"content": "Locus OS"}}]
        },
        children=[
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "This page is managed by Locus OS. "
                                "The databases below are automatically synced."
                            },
                        }
                    ],
                    "icon": {"type": "emoji", "emoji": "🧠"},
                },
            }
        ],
    )
    return page["id"]


async def ensure_notion_databases() -> dict:
    """
    Ensure that the Locus Tasks and Locus Logs databases exist in Notion.
    Returns {"tasks_db_id": ..., "notes_db_id": ...}.
    Uses settings first, then Redis cache, then auto-creates.
    """
    import redis.asyncio as aioredis

    notion = get_notion_client()
    if not notion:
        return {}

    r = aioredis.from_url(settings.REDIS_URL)
    result = {}

    try:
        # Try settings → Redis → search → create for each DB
        for key, redis_key, title, schema in [
            ("tasks_db_id", "notion:tasks_db_id", "Locus Tasks", TASKS_DB_SCHEMA),
            ("notes_db_id", "notion:notes_db_id", "Locus Logs", LOGS_DB_SCHEMA),
        ]:
            # 1) Check settings (.env)
            env_val = getattr(settings, f"NOTION_{key.upper()}", "")
            if env_val:
                result[key] = env_val
                await r.set(redis_key, env_val)
                continue

            # 2) Check Redis cache
            cached = await r.get(redis_key)
            if cached:
                result[key] = cached.decode()
                continue

            # 3) Search Notion for existing DB
            existing = await _find_existing_db(notion, title)
            if existing:
                result[key] = existing
                await r.set(redis_key, existing)
                logger.info(f"Found existing Notion DB '{title}': {existing}")
                continue

            # 4) Create a new one
            parent_page_id = await _find_or_create_parent_page(notion)
            new_id = await _create_database(notion, parent_page_id, title, schema)
            result[key] = new_id
            await r.set(redis_key, new_id)
            logger.info(f"Created Notion DB '{title}': {new_id}")

    except Exception as e:
        logger.error(f"Notion auto-provision error: {e}", exc_info=True)
    finally:
        await r.aclose()

    return result


# ──────────────────────────────────────────────
# Write helpers — used by Engine 1 to sync data
# ──────────────────────────────────────────────

async def sync_task_to_notion(task_data: dict) -> Optional[str]:
    """
    Create or update a task page in the Locus Tasks database.
    Returns the Notion page ID.
    """
    import redis.asyncio as aioredis

    notion = get_notion_client()
    if not notion:
        return None

    r = aioredis.from_url(settings.REDIS_URL)
    try:
        db_id = settings.NOTION_TASKS_DB_ID or (await r.get("notion:tasks_db_id") or b"").decode()
        if not db_id:
            ids = await ensure_notion_databases()
            db_id = ids.get("tasks_db_id", "")
        if not db_id:
            return None

        properties = {
            "Task": {"title": [{"text": {"content": task_data.get("title", "Untitled")}}]},
            "Status": {"select": {"name": task_data.get("status", "pending")}},
            "Source": {"select": {"name": task_data.get("source", "pwa")}},
        }
        if task_data.get("locus_id"):
            properties["Locus ID"] = {"rich_text": [{"text": {"content": task_data["locus_id"]}}]}
        if task_data.get("priority"):
            properties["Priority"] = {"select": {"name": task_data["priority"]}}
        if task_data.get("energy_type"):
            properties["Energy"] = {"select": {"name": task_data["energy_type"]}}
        if task_data.get("deadline"):
            properties["Due Date"] = {"date": {"start": task_data["deadline"]}}

        page = await notion.pages.create(parent={"database_id": db_id}, properties=properties)
        return page["id"]
    except Exception as e:
        logger.error(f"Notion sync_task error: {e}", exc_info=True)
        return None
    finally:
        await r.aclose()


async def log_event_to_notion(event_data: dict) -> Optional[str]:
    """
    Log a behavioral event to the Locus Logs database.
    Returns the Notion page ID.
    """
    import redis.asyncio as aioredis

    notion = get_notion_client()
    if not notion:
        return None

    r = aioredis.from_url(settings.REDIS_URL)
    try:
        db_id = settings.NOTION_NOTES_DB_ID or (await r.get("notion:notes_db_id") or b"").decode()
        if not db_id:
            ids = await ensure_notion_databases()
            db_id = ids.get("notes_db_id", "")
        if not db_id:
            return None

        content = event_data.get("content", "Event logged")
        title = content[:100] if len(content) > 100 else content

        properties = {
            "Title": {"title": [{"text": {"content": title}}]},
            "Type": {"select": {"name": event_data.get("type", "thought")}},
            "Source": {"select": {"name": event_data.get("source", "telegram")}},
            "Logged At": {"date": {"start": event_data.get("created_at", "")}},
        }
        if event_data.get("locus_id"):
            properties["Locus ID"] = {"rich_text": [{"text": {"content": event_data["locus_id"]}}]}
        if event_data.get("mood_indicator") is not None:
            properties["Mood"] = {"number": event_data["mood_indicator"]}

        page = await notion.pages.create(parent={"database_id": db_id}, properties=properties)
        return page["id"]
    except Exception as e:
        logger.error(f"Notion log_event error: {e}", exc_info=True)
        return None
    finally:
        await r.aclose()
