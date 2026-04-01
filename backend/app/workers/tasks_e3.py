from app.workers.celery_app import app
import os
import httpx
import logging

logger = logging.getLogger("engine3")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_TASKS_DB_ID = os.getenv("NOTION_TASKS_DB_ID", "")
NOTION_NOTES_DB_ID = os.getenv("NOTION_NOTES_DB_ID", "")


@app.task(queue="engine3")
def generate_schedule(user_id: str):
    pass


@app.task(queue="engine3", bind=True, max_retries=3)
def sync_task_to_notion(self, task_data: dict):
    """Sync a task from PostgreSQL to Notion.

    Args:
        task_data: dict with keys:
            id, title, status, source, created_at, user_id
    """
    if not NOTION_API_KEY or not NOTION_TASKS_DB_ID:
        logger.info("[Engine3] Notion not configured, skipping sync")
        return

    task_id = task_data.get("id", "")
    title = task_data.get("title", "Untitled")
    status = task_data.get("status", "pending")
    source = task_data.get("source", "pwa")

    try:
        # Check if page already exists (by title match)
        existing = _find_notion_page(task_id)
        if existing:
            logger.info(f"[Engine3] Task {task_id} already in Notion: {existing}")
            return

        # Create new page in Notion tasks database
        _create_notion_page(task_id, title, status, source)
        logger.info(f"[Engine3] Synced task to Notion: {title}")

    except Exception as exc:
        logger.error(f"[Engine3] Notion sync error: {exc}")
        raise self.retry(exc=exc, countdown=60)


def _find_notion_page(task_id: str) -> str | None:
    """Search for a page with matching task ID in the title."""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    body = {
        "filter": {
            "property": "Name",
            "title": {
                "contains": task_id[:8],
            },
        },
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"https://api.notion.com/v1/databases/{NOTION_TASKS_DB_ID}/query",
                headers=headers,
                json=body,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    title_props = (
                        r.get("properties", {}).get("Name", {}).get("title", [])
                    )
                    for t in title_props:
                        if task_id in t.get("plain_text", ""):
                            return r.get("id")
    except Exception as e:
        logger.error(f"[Engine3] Notion search error: {e}")
    return None


def _create_notion_page(task_id: str, title: str, status: str, source: str):
    """Create a new page in the Notion tasks database."""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    # Use only the Name property since that's all that exists
    page_title = f"{title} [{task_id[:8]}]"

    body = {
        "parent": {"database_id": NOTION_TASKS_DB_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": page_title}}],
            },
        },
    }

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=body,
        )
        if resp.status_code == 200:
            return resp.json().get("id")
        else:
            resp.raise_for_status()
