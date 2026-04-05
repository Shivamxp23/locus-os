from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class OpenClawAuditEntry(BaseModel):
    channel: Optional[str] = None
    sessionId: Optional[str] = None
    bodyPreview: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/openclaw")
async def audit_openclaw(request: Request):
    """Receive audit logs from OpenClaw request interceptor."""
    try:
        body = await request.json()
        entry = OpenClawAuditEntry(**body)
        logger.info(
            f"OpenClaw audit: channel={entry.channel} session={entry.sessionId} "
            f"preview={entry.bodyPreview[:100] if entry.bodyPreview else 'none'} "
            f"time={entry.timestamp}"
        )
        return {"status": "logged", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"OpenClaw audit error: {e}")
        return {"status": "error", "detail": str(e)}
