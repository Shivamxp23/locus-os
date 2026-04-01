from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.models import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
async def get_integrations_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Status of all connected integrations for the current user."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    return {
        "notion": {"connected": bool(user.notion_access_token), "last_sync": None},
        "google_calendar": {
            "connected": bool(user.google_refresh_token),
            "last_sync": None,
        },
        "telegram": {
            "connected": bool(user.telegram_chat_id),
            "chat_id": user.telegram_chat_id,
        },
    }
