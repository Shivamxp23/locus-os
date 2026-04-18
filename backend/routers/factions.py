# /opt/locus/backend/routers/factions.py
# Faction health calculation — real data from PostgreSQL

from fastapi import APIRouter
from datetime import date, timedelta
import asyncpg
import os

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")

# Default weekly targets (hours)
FACTION_TARGETS = {
    "health":     17.5,
    "leverage":   20.0,
    "craft":      15.0,
    "expression":  7.5,
}


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


@router.get("/factions/health")
async def faction_health():
    """Calculate real-time faction health for the current week"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    conn = await get_conn()
    try:
        # Actual hours per faction this week
        rows = await conn.fetch("""
            SELECT faction,
                   COUNT(*) FILTER (WHERE status = 'done') AS completed,
                   COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                   COUNT(*) FILTER (WHERE status = 'deferred') AS deferred,
                   COALESCE(SUM(actual_hours) FILTER (WHERE status = 'done'), 0) AS actual_hours,
                   COALESCE(SUM(estimated_hours) FILTER (WHERE status = 'pending'), 0) AS pending_hours
            FROM tasks
            WHERE user_id = 'shivam'
              AND (
                  (status = 'done' AND completed_at >= $1)
                  OR status = 'pending'
              )
            GROUP BY faction
        """, week_start)

        faction_map = {r['faction']: dict(r) for r in rows}

        factions = {}
        for faction, target in FACTION_TARGETS.items():
            data = faction_map.get(faction, {})
            actual = float(data.get('actual_hours', 0))
            completed = int(data.get('completed', 0))
            pending = int(data.get('pending', 0))
            deferred = int(data.get('deferred', 0))
            
            total_tasks = completed + pending + deferred
            completion_rate = round((completed / total_tasks * 100) if total_tasks > 0 else 0)
            lag = round(max(0, target - actual), 1)
            
            # Action gap: (target - actual) / target * 10
            action_gap = round(((target - actual) / target * 10) if target > 0 else 0, 1)
            action_gap = max(0, min(10, action_gap))

            factions[faction] = {
                "target_hours": target,
                "actual_hours": round(actual, 1),
                "lag": lag,
                "completion_rate": completion_rate,
                "action_gap": action_gap,
                "completed": completed,
                "pending": pending,
                "deferred": deferred,
            }

        # Write to faction_stats for historical tracking
        for faction, data in factions.items():
            await conn.execute("""
                INSERT INTO faction_stats (user_id, week_start, faction, target_hours, actual_hours, completion_rate)
                VALUES ('shivam', $1, $2, $3, $4, $5)
                ON CONFLICT (user_id, week_start, faction) DO UPDATE SET
                    actual_hours = EXCLUDED.actual_hours,
                    completion_rate = EXCLUDED.completion_rate
            """, week_start, faction, data['target_hours'], data['actual_hours'], float(data['completion_rate']))

        return {
            "week_start": str(week_start),
            "factions": factions,
        }
    finally:
        await conn.close()


@router.get("/factions/history")
async def faction_history(weeks: int = 8):
    """Get faction stats over the last N weeks"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT week_start, faction, target_hours, actual_hours, completion_rate
            FROM faction_stats
            WHERE user_id = 'shivam'
            ORDER BY week_start DESC
            LIMIT $1
        """, weeks * 4)  # 4 factions per week
        
        # Group by week
        weeks_data = {}
        for r in rows:
            ws = str(r['week_start'])
            if ws not in weeks_data:
                weeks_data[ws] = {}
            weeks_data[ws][r['faction']] = {
                "target": float(r['target_hours']) if r['target_hours'] else 0,
                "actual": float(r['actual_hours']) if r['actual_hours'] else 0,
                "rate": float(r['completion_rate']) if r['completion_rate'] else 0,
            }

        return {"history": weeks_data}
    finally:
        await conn.close()
