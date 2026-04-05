from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.models import Task, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_id: Optional[str] = None
    project_id: Optional[str] = None
    energy_type: Optional[str] = None
    estimated_minutes: Optional[int] = None
    deadline: Optional[datetime] = None
    source: Optional[str] = "pwa"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    goal_id: Optional[str] = None
    energy_type: Optional[str] = None
    estimated_minutes: Optional[int] = None
    deadline: Optional[datetime] = None


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    goal_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.user_id == current_user.id)
    if status:
        q = q.where(Task.status == status)
    if goal_id:
        q = q.where(Task.goal_id == goal_id)
    q = q.order_by(Task.created_at.desc())
    result = await db.execute(q)
    return [_task_dict(t) for t in result.scalars().all()]


@router.post("")
async def create_task(
    req: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = Task(
        user_id=current_user.id,
        title=req.title,
        description=req.description,
        goal_id=req.goal_id,
        project_id=req.project_id,
        energy_type=req.energy_type,
        estimated_minutes=req.estimated_minutes,
        deadline=req.deadline,
        source=req.source or "pwa",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _task_dict(task)


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_or_404(task_id, current_user.id, db)
    return _task_dict(task)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    req: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_or_404(task_id, current_user.id, db)
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(task, k, v)
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_or_404(task_id, current_user.id, db)
    task.status = "cancelled"
    task.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "cancelled"}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_or_404(task_id, current_user.id, db)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    await db.commit()
    return _task_dict(task)


@router.post("/{task_id}/defer")
async def defer_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_or_404(task_id, current_user.id, db)
    task.deferral_count = (task.deferral_count or 0) + 1
    task.status = "deferred"
    task.updated_at = datetime.utcnow()
    await db.commit()
    return _task_dict(task)


async def _get_or_404(task_id: str, user_id: str, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _task_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "source": t.source,
        "goal_id": t.goal_id,
        "project_id": t.project_id,
        "energy_type": t.energy_type,
        "estimated_minutes": t.estimated_minutes,
        "priority_score": t.priority_score,
        "scheduled_at": t.scheduled_at,
        "deferral_count": t.deferral_count,
        "completed_at": t.completed_at,
        "deadline": t.deadline,
        "engine_annotations": t.engine_annotations,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
