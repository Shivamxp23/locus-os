# /opt/locus/backend/routers/analytics_data.py
# Real analytics endpoints — no fake data

from fastapi import APIRouter
from datetime import date, timedelta
import asyncpg
import os

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


@router.get("/analytics/dcs-trend")
async def dcs_trend(days: int = 30):
    """DCS scores over the last N days"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT date, dcs, mode, energy, mood, sleep_quality, stress
            FROM daily_logs
            WHERE user_id = 'shivam' 
              AND checkin_type = 'morning'
              AND date >= NOW() - INTERVAL '1 day' * $1
            ORDER BY date ASC
        """, days)
        return {
            "trend": [
                {
                    "date": str(r['date']),
                    "dcs": float(r['dcs']) if r['dcs'] else None,
                    "mode": r['mode'],
                    "energy": r['energy'],
                    "mood": r['mood'],
                    "sleep_quality": r['sleep_quality'],
                    "stress": r['stress'],
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()


@router.get("/analytics/mood-trend")
async def mood_trend(days: int = 30):
    """Mood scores over time (all check-ins)"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT date, checkin_type, mood
            FROM daily_logs
            WHERE user_id = 'shivam' 
              AND mood IS NOT NULL
              AND date >= NOW() - INTERVAL '1 day' * $1
            ORDER BY date ASC, checkin_type
        """, days)
        return {
            "trend": [
                {"date": str(r['date']), "type": r['checkin_type'], "mood": r['mood']}
                for r in rows
            ]
        }
    finally:
        await conn.close()


@router.get("/analytics/completion-rates")
async def completion_rates(days: int = 30):
    """Task completion rates by faction over time"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT faction,
                   COUNT(*) FILTER (WHERE status = 'done') AS completed,
                   COUNT(*) FILTER (WHERE status = 'deferred') AS deferred,
                   COUNT(*) FILTER (WHERE status = 'killed') AS killed,
                   COUNT(*) AS total,
                   COALESCE(AVG(quality) FILTER (WHERE status = 'done'), 0) AS avg_quality,
                   COALESCE(AVG(actual_hours) FILTER (WHERE status = 'done'), 0) AS avg_actual_hours,
                   COALESCE(AVG(estimated_hours), 0) AS avg_estimated_hours
            FROM tasks
            WHERE user_id = 'shivam'
              AND created_at >= NOW() - INTERVAL '1 day' * $1
            GROUP BY faction
        """, days)
        return {
            "rates": {
                r['faction']: {
                    "completed": r['completed'],
                    "deferred": r['deferred'],
                    "killed": r['killed'],
                    "total": r['total'],
                    "rate": round(r['completed'] / r['total'] * 100 if r['total'] > 0 else 0),
                    "avg_quality": round(float(r['avg_quality']), 1),
                    "avg_actual_hours": round(float(r['avg_actual_hours']), 1),
                    "avg_estimated_hours": round(float(r['avg_estimated_hours']), 1),
                    "estimation_accuracy": round(
                        float(r['avg_actual_hours']) / float(r['avg_estimated_hours']) * 100
                        if float(r['avg_estimated_hours']) > 0 else 0
                    ),
                }
                for r in rows
            }
        }
    finally:
        await conn.close()


@router.get("/analytics/behavioral-patterns")
async def behavioral_patterns(days: int = 14):
    """Recent behavioral events aggregated"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT event_type, COUNT(*) AS count, 
                   MAX(created_at) AS last_seen
            FROM behavioral_events
            WHERE user_id = 'shivam'
              AND created_at >= NOW() - INTERVAL '1 day' * $1
            GROUP BY event_type
            ORDER BY count DESC
        """, days)
        return {
            "patterns": [
                {
                    "event": r['event_type'],
                    "count": r['count'],
                    "last_seen": r['last_seen'].isoformat() if r['last_seen'] else None,
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()


@router.get("/analytics/avoidance-report")
async def avoidance_report():
    """Avoidance patterns from evening check-ins"""
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT avoided, avoided_reason, COUNT(*) AS frequency,
                   MIN(date) AS first_seen, MAX(date) AS last_seen
            FROM daily_logs
            WHERE user_id = 'shivam'
              AND checkin_type = 'evening'
              AND avoided IS NOT NULL
              AND avoided != ''
            GROUP BY avoided, avoided_reason
            ORDER BY frequency DESC
            LIMIT 10
        """)
        return {
            "avoidances": [
                {
                    "what": r['avoided'],
                    "why": r['avoided_reason'],
                    "frequency": r['frequency'],
                    "first_seen": str(r['first_seen']),
                    "last_seen": str(r['last_seen']),
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()


@router.get("/analytics/summary")
async def analytics_summary():
    """Dashboard summary stats"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    conn = await get_conn()
    try:
        # Total stats
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'done') AS total_completed,
                COUNT(*) FILTER (WHERE status = 'pending') AS total_pending,
                COUNT(*) FILTER (WHERE status = 'deferred') AS total_deferred,
                COALESCE(SUM(actual_hours) FILTER (WHERE status = 'done'), 0) AS total_hours_logged,
                COALESCE(AVG(quality) FILTER (WHERE status = 'done'), 0) AS avg_quality
            FROM tasks
            WHERE user_id = 'shivam'
        """)

        # This week
        week_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'done') AS completed_this_week,
                COALESCE(SUM(actual_hours) FILTER (WHERE status = 'done'), 0) AS hours_this_week
            FROM tasks
            WHERE user_id = 'shivam' AND completed_at >= $1
        """, week_start)

        # Check-in streak
        streak = await conn.fetch("""
            SELECT DISTINCT date FROM daily_logs
            WHERE user_id = 'shivam' AND checkin_type = 'morning'
            ORDER BY date DESC LIMIT 30
        """)

        # Calculate consecutive days
        streak_count = 0
        expected = today
        for r in streak:
            if r['date'] == expected:
                streak_count += 1
                expected -= timedelta(days=1)
            else:
                break

        return {
            "total_completed": stats['total_completed'],
            "total_pending": stats['total_pending'],
            "total_deferred": stats['total_deferred'],
            "total_hours_logged": round(float(stats['total_hours_logged']), 1),
            "avg_quality": round(float(stats['avg_quality']), 1),
            "completed_this_week": week_stats['completed_this_week'],
            "hours_this_week": round(float(week_stats['hours_this_week']), 1),
            "checkin_streak": streak_count,
        }
    finally:
        await conn.close()
