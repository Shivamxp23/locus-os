from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import uuid
import json
from app.database import get_db
from app.models.models import (
    User,
    SyncEvent,
    Task,
    Goal,
    PersonalitySnapshot,
    BehavioralEvent,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/sync", tags=["sync"])


class OfflineQueueItem(BaseModel):
    id: str
    created_at: int
    type: str
    payload: dict
    sync_status: str = "pending"
    retry_count: int = 0
    last_retry: Optional[int] = None
    device_id: str


class SyncFlushRequest(BaseModel):
    items: List[OfflineQueueItem]


@router.post("/flush")
async def flush_offline_queue(
    req: SyncFlushRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Flush offline queue (batch endpoint).
    Accepts array of OfflineQueueItem objects.
    Returns {processed, conflicts, errors}.
    Idempotent via UNIQUE(user_id, client_event_id) on sync_events.
    """
    processed = 0
    conflicts = 0
    errors = []

    for item in req.items:
        try:
            # Check idempotency — skip if already synced
            existing = await db.execute(
                select(SyncEvent).where(
                    SyncEvent.user_id == current_user.id,
                    SyncEvent.client_event_id == item.id,
                )
            )
            if existing.scalar_one_or_none():
                conflicts += 1
                continue

            # Route based on event type
            await _process_sync_item(item, current_user.id, db)

            # Record the sync event
            sync_event = SyncEvent(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                device_id=item.device_id,
                client_event_id=item.id,
                event_type=item.type,
                payload=item.payload,
                synced_at=datetime.utcnow(),
            )
            db.add(sync_event)
            processed += 1

        except Exception as e:
            errors.append({"item_id": item.id, "type": item.type, "error": str(e)})

    await db.commit()

    return {"processed": processed, "conflicts": conflicts, "errors": errors}


@router.get("/snapshot")
async def get_sync_snapshot(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Download latest personality snapshot.
    If none exists, returns a lightweight snapshot built from current task/goal state.
    """
    # Try to get latest personality snapshot
    result = await db.execute(
        select(PersonalitySnapshot)
        .where(PersonalitySnapshot.user_id == current_user.id)
        .order_by(PersonalitySnapshot.generated_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()

    if snapshot:
        return snapshot.snapshot_data

    # Build lightweight fallback snapshot from current state
    tasks_result = await db.execute(
        select(Task)
        .where(
            Task.user_id == current_user.id, Task.status.in_(["pending", "in_progress"])
        )
        .limit(50)
    )
    tasks = tasks_result.scalars().all()

    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id, Goal.is_active == True)
        .limit(20)
    )
    goals = goals_result.scalars().all()

    # Recent behavioral summary
    metrics = await db.execute(
        select(
            func.count(BehavioralEvent.id), func.avg(BehavioralEvent.mood_indicator)
        ).where(
            BehavioralEvent.user_id == current_user.id,
            BehavioralEvent.created_at
            >= datetime.utcnow().replace(hour=0, minute=0, second=0),
        )
    )
    row = metrics.one()
    event_count = row[0] or 0
    avg_mood = float(row[1]) if row[1] else 0.0

    fallback_snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user.id),
        "is_fallback": True,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "source": t.source,
                "deferral_count": t.deferral_count or 0,
            }
            for t in tasks
        ],
        "goals": [
            {
                "id": str(g.id),
                "title": g.title,
                "horizon": g.horizon,
                "progress_score": g.progress_score or 0.0,
                "is_active": g.is_active,
            }
            for g in goals
        ],
        "behavioral_summary": {
            "events_today": event_count,
            "avg_mood": round(avg_mood, 2),
        },
    }

    return fallback_snapshot


@router.get("/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Check if user has pending sync items server-side.
    """
    # Latest sync event for this user
    result = await db.execute(
        select(SyncEvent)
        .where(SyncEvent.user_id == current_user.id)
        .order_by(SyncEvent.synced_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "last_sync": latest.synced_at.isoformat() if latest else None,
        "pending_server_items": 0,
    }


async def _process_sync_item(item: OfflineQueueItem, user_id: str, db: AsyncSession):
    """Route a sync item to the correct database operation."""

    if item.type == "task_create":
        task = Task(
            id=item.id,
            user_id=user_id,
            title=item.payload.get("title", ""),
            description=item.payload.get("description", ""),
            source=item.payload.get("source", "pwa"),
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(task)

    elif item.type == "task_complete":
        task_id = item.payload.get("task_id") or item.id
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()

    elif item.type == "task_defer":
        task_id = item.payload.get("task_id") or item.id
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.deferral_count = (task.deferral_count or 0) + 1
            task.updated_at = datetime.utcnow()

    elif item.type == "task_update":
        task_id = item.payload.get("task_id") or item.id
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task:
            for key in (
                "title",
                "description",
                "status",
                "energy_type",
                "estimated_minutes",
                "deadline",
                "goal_id",
                "project_id",
            ):
                if key in item.payload:
                    setattr(task, key, item.payload[key])
            task.updated_at = datetime.utcnow()

    elif item.type == "log_entry":
        event = BehavioralEvent(
            id=item.id,
            user_id=user_id,
            source=item.payload.get("source", "pwa"),
            event_type=item.payload.get("event_type", "log"),
            raw_content=item.payload.get("content", ""),
            created_at=datetime.utcnow(),
            received_at=datetime.utcnow(),
        )
        db.add(event)

    elif item.type == "voice_note":
        event = BehavioralEvent(
            id=item.id,
            user_id=user_id,
            source="pwa",
            event_type="voice_note",
            raw_content=item.payload.get("transcription", ""),
            created_at=datetime.utcnow(),
            received_at=datetime.utcnow(),
        )
        db.add(event)

    else:
        raise ValueError(f"Unknown sync item type: {item.type}")
