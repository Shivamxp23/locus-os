# /opt/locus/backend/routers/schedule.py
# Schedule generation endpoints — Engine 3

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import asyncpg
import os
from datetime import date, timedelta

from services.scheduler_engine import (
    TaskItem, FactionHealth, ScheduleConfig, ScheduleResult,
    generate_schedule, DEFAULT_FACTION_TARGETS
)

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


class ScheduleRequest(BaseModel):
    available_hours: Optional[float] = 8.0


@router.get("/schedule/today")
async def get_today_schedule():
    """Generate today's schedule based on current DCS and pending tasks"""
    today = date.today()
    conn = await get_conn()
    try:
        # 1. Get today's DCS
        log_row = await conn.fetchrow("""
            SELECT dcs, mode FROM daily_logs
            WHERE user_id = 'shivam' AND date = $1 AND checkin_type = 'morning'
        """, today)

        dcs = float(log_row['dcs']) if log_row and log_row['dcs'] else 5.0
        mode = log_row['mode'] if log_row and log_row['mode'] else 'NORMAL'

        # 2. Get time available (from morning check-in or default)
        available_hours = 8.0  # Default

        # 3. Get all pending tasks
        task_rows = await conn.fetch("""
            SELECT id, title, faction, priority, urgency, difficulty,
                   tws, estimated_hours, deferral_count, scheduled_date
            FROM tasks
            WHERE user_id = 'shivam' AND status = 'pending'
            ORDER BY tws DESC
        """)

        tasks = [
            TaskItem(
                id=str(r['id']),
                title=r['title'],
                faction=r['faction'],
                priority=r['priority'],
                urgency=r['urgency'],
                difficulty=r['difficulty'],
                tws=float(r['tws']) if r['tws'] else 0.0,
                estimated_hours=float(r['estimated_hours']) if r['estimated_hours'] else 1.0,
                deferral_count=r['deferral_count'] or 0,
                scheduled_date=str(r['scheduled_date']) if r['scheduled_date'] else None,
            )
            for r in task_rows
        ]

        # 4. Get faction health for this week
        week_start = today - timedelta(days=today.weekday())
        faction_rows = await conn.fetch("""
            SELECT faction, 
                   COALESCE(SUM(actual_hours), 0) AS actual_hours
            FROM tasks
            WHERE user_id = 'shivam' 
              AND status = 'done'
              AND completed_at >= $1
            GROUP BY faction
        """, week_start)

        actual_map = {r['faction']: float(r['actual_hours']) for r in faction_rows}

        faction_health = [
            FactionHealth(
                faction=f,
                target_hours=target,
                actual_hours=actual_map.get(f, 0.0),
            )
            for f, target in DEFAULT_FACTION_TARGETS.items()
        ]

        # 5. Run the scheduling algorithm
        config = ScheduleConfig(
            dcs=dcs,
            mode=mode,
            available_hours=available_hours,
        )

        result = generate_schedule(tasks, faction_health, config)

        return {
            "date": str(today),
            "mode": result.mode,
            "dcs": result.dcs,
            "total_hours": result.total_hours,
            "available_hours": result.available_hours,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "faction": t.faction,
                    "estimated_hours": t.estimated_hours,
                    "difficulty": t.difficulty,
                    "adjusted_tws": round(t.adjusted_tws, 2),
                    "deferral_count": t.deferral_count,
                }
                for t in result.tasks
            ],
            "faction_breakdown": result.faction_breakdown,
            "formatted": result.message,
        }
    finally:
        await conn.close()


@router.post("/schedule/generate")
async def generate_custom_schedule(req: ScheduleRequest):
    """Generate schedule with custom available hours"""
    today = date.today()
    conn = await get_conn()
    try:
        log_row = await conn.fetchrow("""
            SELECT dcs, mode FROM daily_logs
            WHERE user_id = 'shivam' AND date = $1 AND checkin_type = 'morning'
        """, today)

        dcs = float(log_row['dcs']) if log_row and log_row['dcs'] else 5.0
        mode = log_row['mode'] if log_row and log_row['mode'] else 'NORMAL'

        task_rows = await conn.fetch("""
            SELECT id, title, faction, priority, urgency, difficulty,
                   tws, estimated_hours, deferral_count, scheduled_date
            FROM tasks
            WHERE user_id = 'shivam' AND status = 'pending'
            ORDER BY tws DESC
        """)

        tasks = [
            TaskItem(
                id=str(r['id']),
                title=r['title'],
                faction=r['faction'],
                priority=r['priority'],
                urgency=r['urgency'],
                difficulty=r['difficulty'],
                tws=float(r['tws']) if r['tws'] else 0.0,
                estimated_hours=float(r['estimated_hours']) if r['estimated_hours'] else 1.0,
                deferral_count=r['deferral_count'] or 0,
            )
            for r in task_rows
        ]

        week_start = today - timedelta(days=today.weekday())
        faction_rows = await conn.fetch("""
            SELECT faction, COALESCE(SUM(actual_hours), 0) AS actual_hours
            FROM tasks
            WHERE user_id = 'shivam' AND status = 'done' AND completed_at >= $1
            GROUP BY faction
        """, week_start)

        actual_map = {r['faction']: float(r['actual_hours']) for r in faction_rows}

        faction_health = [
            FactionHealth(
                faction=f,
                target_hours=target,
                actual_hours=actual_map.get(f, 0.0),
            )
            for f, target in DEFAULT_FACTION_TARGETS.items()
        ]

        config = ScheduleConfig(
            dcs=dcs,
            mode=mode,
            available_hours=req.available_hours or 8.0,
        )

        result = generate_schedule(tasks, faction_health, config)

        return {
            "date": str(today),
            "mode": result.mode,
            "dcs": result.dcs,
            "total_hours": result.total_hours,
            "available_hours": result.available_hours,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "faction": t.faction,
                    "estimated_hours": t.estimated_hours,
                    "difficulty": t.difficulty,
                    "adjusted_tws": round(t.adjusted_tws, 2),
                }
                for t in result.tasks
            ],
            "faction_breakdown": result.faction_breakdown,
            "formatted": result.message,
        }
    finally:
        await conn.close()
