"""
Morning log, evening log, and daily logging endpoints.
Phase 1A — core logging engine (F-001, DCS computation, smart response).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
import uuid
import logging

from app.database import get_db
from app.models.models import User
from app.services.auth import get_current_user
from app.engines.e1.dcs import calculate_dcs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/log", tags=["log"])


class MorningLogRequest(BaseModel):
    energy: int = Field(..., ge=1, le=10, description="Energy 1-10")
    mood: int = Field(..., ge=1, le=10, description="Mood 1-10")
    sleep: int = Field(..., ge=1, le=10, description="Sleep quality 1-10")
    stress: int = Field(..., ge=1, le=10, description="Stress 1-10")
    time_available: float = Field(..., gt=0, description="Available hours today")


class EveningLogRequest(BaseModel):
    what_i_did: str
    what_i_avoided: Optional[str] = None
    tomorrow_priority: Optional[str] = None


@router.post("/morning")
async def morning_log(
    req: MorningLogRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Log morning metrics: E, M, S, ST, T.
    Computes DCS, determines operating mode, returns contextual response.
    F-001, F-002.
    """
    try:
        result = calculate_dcs(req.energy, req.mood, req.sleep, req.stress)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Write behavioral event (F-006) — simple log for now
    logger.info(
        f"Morning log: user={current_user.id} "
        f"E={req.energy} M={req.mood} S={req.sleep} ST={req.stress} T={req.time_available} "
        f"DCS={result.score} mode={result.mode.value}"
    )

    return {
        "dcs": result.score,
        "mode": result.mode.value,
        "mode_description": result.mode_description,
        "recommended_task_types": result.recommended_task_types,
        "metrics": {
            "energy": req.energy,
            "mood": req.mood,
            "sleep": req.sleep,
            "stress": req.stress,
            "time_available": req.time_available,
        },
        "logged_at": datetime.utcnow().isoformat(),
    }


@router.post("/evening")
async def evening_log(
    req: EveningLogRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Log evening reflection: what I did, what I avoided, tomorrow's priority.
    F-007.
    """
    logger.info(
        f"Evening log: user={current_user.id} "
        f"did={req.what_i_did[:50]} avoided={str(req.what_i_avoided)[:50]}"
    )
    return {
        "status": "logged",
        "tomorrow_priority": req.tomorrow_priority,
        "logged_at": datetime.utcnow().isoformat(),
    }
