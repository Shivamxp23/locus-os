# /opt/locus/backend/routers/goals.py
# Goal Stack: Outcomes → Projects → Tasks
# Implements the core hierarchy from LOCUS_SYSTEM_v1.md §5-6

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


# ── DB Migration — run on first call ──

async def ensure_outcomes_table():
    """Create the outcomes table if it doesn't exist"""
    conn = await get_conn()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id TEXT NOT NULL DEFAULT 'shivam',
                title TEXT NOT NULL,
                description TEXT,
                faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
                status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','completed','abandoned')),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Add outcome_id to projects if not exists
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='projects' AND column_name='outcome_id'
                ) THEN
                    ALTER TABLE projects ADD COLUMN outcome_id UUID REFERENCES outcomes(id);
                END IF;
            END $$
        """)
    finally:
        await conn.close()


# ── Models ──

class OutcomeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    faction: str = Field(..., pattern="^(health|leverage|craft|expression)$")

class OutcomeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    faction: str = Field(..., pattern="^(health|leverage|craft|expression)$")
    outcome_id: Optional[str] = None
    target_hours_weekly: Optional[float] = None
    deadline: Optional[date] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    outcome_id: Optional[str] = None
    target_hours_weekly: Optional[float] = None
    deadline: Optional[date] = None

class TaskBreakdown(BaseModel):
    project_id: str
    description: str  # Free text — AI will break it down


# ── Outcomes CRUD ──

@router.post("/outcomes")
async def create_outcome(data: OutcomeCreate):
    await ensure_outcomes_table()
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            INSERT INTO outcomes (user_id, title, description, faction)
            VALUES ('shivam', $1, $2, $3)
            RETURNING id, title, faction, status, created_at
        """, data.title, data.description, data.faction)
        return {"status": "ok", "outcome": dict(row)}
    finally:
        await conn.close()


@router.get("/outcomes")
async def get_outcomes(status: str = "active"):
    await ensure_outcomes_table()
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT o.id, o.title, o.description, o.faction, o.status, o.created_at,
                   COUNT(p.id) AS project_count
            FROM outcomes o
            LEFT JOIN projects p ON p.outcome_id = o.id AND p.status = 'active'
            WHERE o.user_id = 'shivam' AND o.status = $1
            GROUP BY o.id
            ORDER BY o.faction, o.created_at
        """, status)
        return {"outcomes": [dict(r) for r in rows]}
    finally:
        await conn.close()


@router.get("/outcomes/{outcome_id}")
async def get_outcome_detail(outcome_id: str):
    await ensure_outcomes_table()
    conn = await get_conn()
    try:
        outcome = await conn.fetchrow("""
            SELECT * FROM outcomes WHERE id = $1 AND user_id = 'shivam'
        """, outcome_id)
        if not outcome:
            return {"status": "error", "message": "Outcome not found"}

        projects = await conn.fetch("""
            SELECT p.*, 
                   COUNT(t.id) FILTER (WHERE t.status = 'pending') AS pending_tasks,
                   COUNT(t.id) FILTER (WHERE t.status = 'done') AS completed_tasks
            FROM projects p
            LEFT JOIN tasks t ON t.parent_project_id = p.id
            WHERE p.outcome_id = $1 AND p.user_id = 'shivam'
            GROUP BY p.id
            ORDER BY p.status, p.created_at
        """, outcome_id)

        return {
            "outcome": dict(outcome),
            "projects": [dict(p) for p in projects]
        }
    finally:
        await conn.close()


@router.put("/outcomes/{outcome_id}")
async def update_outcome(outcome_id: str, data: OutcomeUpdate):
    conn = await get_conn()
    try:
        updates = []
        params = []
        idx = 1
        for field_name, value in data.dict(exclude_none=True).items():
            updates.append(f"{field_name} = ${idx}")
            params.append(value)
            idx += 1
        if not updates:
            return {"status": "error", "message": "No fields to update"}
        params.append(outcome_id)
        query = f"""
            UPDATE outcomes SET {', '.join(updates)}
            WHERE id = ${idx} AND user_id = 'shivam'
            RETURNING id, title, faction, status
        """
        row = await conn.fetchrow(query, *params)
        return {"status": "ok", "outcome": dict(row) if row else None}
    finally:
        await conn.close()


# ── Projects CRUD ──

@router.post("/projects")
async def create_project(data: ProjectCreate):
    await ensure_outcomes_table()
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            INSERT INTO projects (
                user_id, title, description, faction, 
                outcome_id, target_hours_weekly, deadline
            ) VALUES ('shivam', $1, $2, $3, $4, $5, $6)
            RETURNING id, title, faction, status, created_at
        """, data.title, data.description, data.faction,
            data.outcome_id, data.target_hours_weekly, data.deadline)

        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'project_create', $1)
        """, f'{{"title": "{data.title[:80]}", "faction": "{data.faction}"}}')

        return {"status": "ok", "project": dict(row)}
    finally:
        await conn.close()


@router.get("/projects")
async def get_projects(status: str = "active", faction: Optional[str] = None):
    conn = await get_conn()
    try:
        query = """
            SELECT p.*, o.title AS outcome_title,
                   COUNT(t.id) FILTER (WHERE t.status = 'pending') AS pending_tasks,
                   COUNT(t.id) FILTER (WHERE t.status = 'done') AS completed_tasks,
                   COALESCE(SUM(t.actual_hours) FILTER (WHERE t.status = 'done'), 0) AS total_hours_spent
            FROM projects p
            LEFT JOIN outcomes o ON o.id = p.outcome_id
            LEFT JOIN tasks t ON t.parent_project_id = p.id
            WHERE p.user_id = 'shivam' AND p.status = $1
        """
        params = [status]
        if faction:
            query += " AND p.faction = $2"
            params.append(faction)
        query += " GROUP BY p.id, o.title ORDER BY p.faction, p.created_at DESC"
        
        rows = await conn.fetch(query, *params)
        return {"projects": [dict(r) for r in rows]}
    finally:
        await conn.close()


@router.get("/projects/{project_id}")
async def get_project_detail(project_id: str):
    conn = await get_conn()
    try:
        project = await conn.fetchrow("""
            SELECT p.*, o.title AS outcome_title
            FROM projects p
            LEFT JOIN outcomes o ON o.id = p.outcome_id
            WHERE p.id = $1 AND p.user_id = 'shivam'
        """, project_id)
        if not project:
            return {"status": "error", "message": "Project not found"}

        tasks = await conn.fetch("""
            SELECT id, title, faction, priority, urgency, difficulty, 
                   tws, estimated_hours, actual_hours, status, deferral_count,
                   scheduled_date, completed_at
            FROM tasks
            WHERE parent_project_id = $1 AND user_id = 'shivam'
            ORDER BY status, tws DESC
        """, project_id)

        return {
            "project": dict(project),
            "tasks": [dict(t) for t in tasks]
        }
    finally:
        await conn.close()


@router.put("/projects/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate):
    conn = await get_conn()
    try:
        updates = []
        params = []
        idx = 1
        for field_name, value in data.dict(exclude_none=True).items():
            updates.append(f"{field_name} = ${idx}")
            params.append(value)
            idx += 1
        if not updates:
            return {"status": "error", "message": "No fields to update"}

        updates.append(f"last_activity_at = NOW()")
        params.append(project_id)
        query = f"""
            UPDATE projects SET {', '.join(updates)}
            WHERE id = ${idx} AND user_id = 'shivam'
            RETURNING id, title, faction, status
        """
        row = await conn.fetchrow(query, *params)
        return {"status": "ok", "project": dict(row) if row else None}
    finally:
        await conn.close()


# ── Goal Stack Overview ──

@router.get("/goals/stack")
async def goal_stack():
    """Full Goal Stack: Outcomes → Projects → Task counts, grouped by faction"""
    await ensure_outcomes_table()
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT 
                o.id AS outcome_id, o.title AS outcome_title, o.faction,
                p.id AS project_id, p.title AS project_title, p.status AS project_status,
                COUNT(t.id) FILTER (WHERE t.status = 'pending') AS pending_tasks,
                COUNT(t.id) FILTER (WHERE t.status = 'done') AS completed_tasks
            FROM outcomes o
            LEFT JOIN projects p ON p.outcome_id = o.id
            LEFT JOIN tasks t ON t.parent_project_id = p.id
            WHERE o.user_id = 'shivam' AND o.status = 'active'
            GROUP BY o.id, p.id
            ORDER BY o.faction, o.title, p.title
        """)

        # Group by faction → outcome → projects
        stack = {}
        for r in rows:
            f = r["faction"]
            if f not in stack:
                stack[f] = {}
            oid = str(r["outcome_id"])
            if oid not in stack[f]:
                stack[f][oid] = {
                    "id": oid,
                    "title": r["outcome_title"],
                    "projects": []
                }
            if r["project_id"]:
                stack[f][oid]["projects"].append({
                    "id": str(r["project_id"]),
                    "title": r["project_title"],
                    "status": r["project_status"],
                    "pending_tasks": r["pending_tasks"],
                    "completed_tasks": r["completed_tasks"],
                })

        # Convert to list format
        result = {}
        for faction, outcomes in stack.items():
            result[faction] = list(outcomes.values())

        return {"goal_stack": result}
    finally:
        await conn.close()
