from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.database import get_db
from app.models.models import Goal, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/goals", tags=["goals"])

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    horizon: Optional[str] = None
    deadline: Optional[date] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    horizon: Optional[str] = None
    deadline: Optional[date] = None
    is_active: Optional[bool] = None
    progress_score: Optional[float] = None

@router.get("")
async def list_goals(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at.desc()))
    return [_goal_dict(g) for g in result.scalars().all()]

@router.post("")
async def create_goal(req: GoalCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    goal = Goal(
        user_id=current_user.id,
        title=req.title,
        description=req.description,
        horizon=req.horizon,
        deadline=req.deadline,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return _goal_dict(goal)

@router.get("/{goal_id}")
async def get_goal(goal_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    goal = await _get_or_404(goal_id, current_user.id, db)
    return _goal_dict(goal)

@router.patch("/{goal_id}")
async def update_goal(goal_id: str, req: GoalUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    goal = await _get_or_404(goal_id, current_user.id, db)
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(goal, k, v)
    goal.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(goal)
    return _goal_dict(goal)

@router.post("/{goal_id}/progress")
async def update_progress(goal_id: str, progress: float, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    goal = await _get_or_404(goal_id, current_user.id, db)
    goal.progress_score = max(0.0, min(1.0, progress))
    goal.updated_at = datetime.utcnow()
    await db.commit()
    return _goal_dict(goal)

async def _get_or_404(goal_id: str, user_id: str, db: AsyncSession) -> Goal:
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

def _goal_dict(g: Goal) -> dict:
    return {
        "id": g.id, "title": g.title, "description": g.description,
        "horizon": g.horizon, "progress_score": g.progress_score,
        "is_active": g.is_active, "is_stale": g.is_stale,
        "deadline": g.deadline, "notion_page_id": g.notion_page_id,
        "created_at": g.created_at, "updated_at": g.updated_at,
        "last_task_completed": g.last_task_completed
    }
