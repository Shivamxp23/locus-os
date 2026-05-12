from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.brain.collector import run_nightly_crawl
from services.brain.reader import read_vault_file, ReadRequest
from services.brain.retriever import retrieve
from services.brain.scheduler import generate_schedule, reschedule, RescheduleRequest
from services.brain.pattern_engine import run_weekly as get_patterns
from services.brain.goal_tracker import run_weekly_review
from services.brain.pipeline import execute_query
from services.goal_distiller import distill_goals, get_clarification_prompt, is_vague

router = APIRouter(prefix="/brain", tags=["Brain"])

class QueryRequest(BaseModel):
    query: str

class ChatRequest(BaseModel):
    message: str

@router.post("/collect")
async def api_collect():
    result = await run_nightly_crawl()
    return result

@router.post("/read")
async def api_read(request: ReadRequest):
    return await read_vault_file(request.file_path)

@router.post("/retrieve")
async def api_retrieve(request: QueryRequest):
    return await retrieve(request.query)

@router.post("/schedule")
async def api_schedule():
    return await generate_schedule()

@router.post("/reschedule")
async def api_reschedule(request: RescheduleRequest):
    return await reschedule(request.reason, request.lost_hours)

@router.get("/patterns")
async def api_patterns():
    return await get_patterns()

@router.get("/goals")
async def api_goals():
    # In a full implementation, this would fetch from the goal stack (projects/tasks)
    import asyncpg, os
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        rows = await conn.fetch("SELECT id, title, faction, status, deadline FROM projects WHERE status = 'active'")
        return {"active_projects": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.get("/weekly-review")
async def api_weekly_review():
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

@router.post("/chat")
async def api_chat(request: ChatRequest):
    response = await execute_query(request.message)
    return {"reply": response}
