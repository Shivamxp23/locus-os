# /opt/locus/backend/routers/tasks.py — REAL implementation

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
import asyncpg
import os
from datetime import date

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

def calculate_tws(p: int, u: int, d: int) -> float:
    return round((p * 0.4) + (u * 0.4) + (d * 0.2), 2)

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    faction: str = Field(..., pattern="^(health|leverage|craft|expression)$")
    priority: int = Field(..., ge=1, le=10)
    urgency: int = Field(..., ge=1, le=10)
    difficulty: int = Field(..., ge=1, le=10)
    estimated_hours: Optional[float] = None
    scheduled_date: Optional[date] = None

class TaskComplete(BaseModel):
    actual_hours: float
    quality: int = Field(..., ge=1, le=10)
    deviation_reason: Optional[str] = None

class TaskDefer(BaseModel):
    reason: Optional[str] = None

@router.post("/tasks")
async def create_task(task: TaskCreate):
    tws = calculate_tws(task.priority, task.urgency, task.difficulty)
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            INSERT INTO tasks (
                user_id, title, description, faction,
                priority, urgency, difficulty,
                estimated_hours, scheduled_date, status
            ) VALUES ('shivam', $1, $2, $3, $4, $5, $6, $7, $8, 'pending')
            RETURNING id, tws
        """, task.title, task.description, task.faction,
        task.priority, task.urgency, task.difficulty,
        task.estimated_hours, task.scheduled_date)
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'task_create', $1)
        """, f'{{"title": "{task.title[:80]}", "faction": "{task.faction}", "tws": {tws}}}')
    finally:
        await conn.close()

    # Sync to Neo4j + Qdrant (fire-and-forget)
    import asyncio
    asyncio.create_task(_sync_task(task))

    return {"status": "ok", "id": str(row['id']), "tws": float(row['tws'])}


async def _sync_task(task):
    """Background sync to Neo4j + Qdrant."""
    try:
        from services.sync_layer import sync_task_create
        await sync_task_create(
            title=task.title,
            faction=task.faction,
            priority=task.priority,
            urgency=task.urgency,
            difficulty=task.difficulty,
            description=task.description,
            estimated_hours=task.estimated_hours or 1.0,
            source="api",
        )
    except Exception:
        pass  # Non-fatal, logged inside sync_layer

@router.get("/tasks/today")
async def tasks_today():
    today = date.today()
    conn = await get_conn()
    try:
        # Get today's DCS
        log = await conn.fetchrow("""
            SELECT dcs, mode FROM daily_logs
            WHERE user_id = 'shivam' AND date = $1 AND checkin_type = 'morning'
        """, today)
        
        dcs = log['dcs'] if log else 5.0
        mode = log['mode'] if log else 'NORMAL'
        
        # Filter by difficulty based on mode
        max_difficulty = {
            'SURVIVAL': 0, 'RECOVERY': 4, 'NORMAL': 7, 'DEEP_WORK': 9, 'PEAK': 10
        }.get(mode, 7)
        
        rows = await conn.fetch("""
            SELECT id, title, faction, priority, urgency, difficulty, tws,
                   estimated_hours, scheduled_date, status
            FROM tasks
            WHERE user_id = 'shivam' 
              AND status = 'pending'
              AND difficulty <= $1
            ORDER BY tws DESC LIMIT 10
        """, max_difficulty)
        
        tasks = [dict(r) for r in rows]
        
        formatted = f"Mode: {mode} (DCS: {dcs})\n\n"
        if tasks:
            for t in tasks[:5]:
                faction_emoji = {"health":"🟢","leverage":"🔵","craft":"🟠","expression":"🟣"}.get(t['faction'],'⚪')
                formatted += f"{faction_emoji} {t['title']} (TWS: {t['tws']})\n"
        else:
            formatted = "No tasks yet. Add them at locusapp.online"
        
        return {"tasks": tasks, "formatted": formatted, "mode": mode, "dcs": dcs}
    finally:
        await conn.close()

@router.get("/tasks")
async def get_all_tasks(status: str = "pending", faction: Optional[str] = None):
    conn = await get_conn()
    try:
        query = "SELECT * FROM tasks WHERE user_id = 'shivam' AND status = $1"
        params = [status]
        if faction:
            query += " AND faction = $2"
            params.append(faction)
        query += " ORDER BY tws DESC"
        rows = await conn.fetch(query, *params)
        return {"tasks": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, data: TaskComplete):
    conn = await get_conn()
    try:
        from datetime import datetime
        row = await conn.fetchrow("""
            UPDATE tasks SET
                status = 'done',
                actual_hours = $1,
                quality = $2,
                completed_at = NOW()
            WHERE id = $3 AND user_id = 'shivam'
            RETURNING title, faction, tws
        """, data.actual_hours, data.quality, task_id)
        
        if not row:
            return {"status": "error", "message": "Task not found"}
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'task_complete', $1)
        """, f'{{"title": "{row["title"][:80]}", "quality": {data.quality}, "actual_hours": {data.actual_hours}}}')
    finally:
        await conn.close()
    
    return {"status": "ok", "message": f"Task completed. Quality: {data.quality}/10"}

@router.post("/tasks/{task_id}/defer")
async def defer_task(task_id: str, data: TaskDefer = TaskDefer()):
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            UPDATE tasks SET
                status = 'deferred',
                deferral_count = deferral_count + 1
            WHERE id = $1 AND user_id = 'shivam'
            RETURNING title, deferral_count
        """, task_id)
        
        if not row:
            return {"status": "error", "message": "Task not found"}
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'task_defer', $1)
        """, f'{{"title": "{row["title"][:80]}", "deferral_count": {row["deferral_count"]}, "reason": "{(data.reason or "")[:100]}"}}')
        
        alert = ""
        if row['deferral_count'] >= 3:
            alert = f" ⚠️ Deferred {row['deferral_count']} times — pattern detected."
    finally:
        await conn.close()
    
    return {"status": "ok", "message": f"Task deferred.{alert}", "deferral_count": row['deferral_count']}