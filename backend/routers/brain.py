"""
brain.py — Brain Module Router

Exposes endpoints for vault crawl, pattern engine, goal tracker,
and goal distiller. Old pipeline/retriever/scheduler/generator
endpoints have been removed — all conversation routing now goes
through the core/ pipeline in telegram_bot.py.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.brain.collector import run_nightly_crawl
from services.brain.pattern_engine import run_weekly as get_patterns
from services.brain.goal_tracker import run_weekly_review
from services.goal_distiller import distill_goals, get_clarification_prompt

router = APIRouter(prefix="/brain", tags=["Brain"])


@router.post("/collect")
async def api_collect():
    """Trigger a vault crawl + Qdrant indexing."""
    result = await run_nightly_crawl()
    return result


@router.get("/patterns")
async def api_patterns():
    """Run the legacy pattern engine (DCS trend, faction lag, deferral analysis)."""
    return await get_patterns()


@router.get("/goals")
async def api_goals():
    """Fetch active projects from PostgreSQL."""
    import asyncpg, os
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        rows = await conn.fetch("SELECT id, title, faction, status, deadline FROM projects WHERE status = 'active'")
        return {"active_projects": [dict(r) for r in rows]}
    finally:
        await conn.close()


@router.get("/weekly-review")
async def api_weekly_review():
    """Run the weekly goal tracker review."""
    return await run_weekly_review()


@router.post("/goals/distill")
async def api_goals_distill():
    """Parse Goals.md, return distilled goals + projects + vague goals needing clarification."""
    distilled = distill_goals()
    return distilled


@router.get("/goals/clarification/{goal_title}")
async def api_goal_clarification(goal_title: str):
    """Get clarification questions for a vague goal."""
    goals = distill_goals().get("vague_goals", [])
    for g in goals:
        if goal_title.lower() in g.get("title", "").lower():
            return {"questions": get_clarification_prompt(g).split("\n")}
    return {"questions": ["Goal not found in vague goals"]}
