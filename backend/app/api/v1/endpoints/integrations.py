from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.models import User
from app.services.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
async def get_integrations_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Status of all connected integrations for the current user.

    Notion uses a system-level internal API key (NOTION_API_KEY),
    so we check that at the system level rather than per-user.
    Google Calendar and Telegram use per-user OAuth/chat_id tokens.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    # Notion: system-level check — is the API key configured and databases provisioned?
    notion_system_connected = bool(
        settings.NOTION_API_KEY
        and settings.NOTION_TASKS_DB_ID
        and settings.NOTION_NOTES_DB_ID
    )

    return {
        "notion": {
            "connected": notion_system_connected,
            "last_sync": None,
        },
        "google_calendar": {
            "connected": bool(user.google_refresh_token),
            "last_sync": None,
        },
        "telegram": {
            "connected": bool(user.telegram_chat_id),
            "chat_id": user.telegram_chat_id,
        },
    }
