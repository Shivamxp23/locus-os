from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.skills.locus.brain.collector import run_nightly_crawl
from backend.skills.locus.brain.reader import read_vault_file, ReadRequest
from backend.skills.locus.brain.retriever import retrieve
from backend.skills.locus.brain.scheduler import generate_schedule, reschedule, RescheduleRequest
from backend.skills.locus.brain.pattern_engine import run_weekly as get_patterns
from backend.skills.locus.brain.goal_tracker import run_weekly_review
from backend.skills.locus.brain.pipeline import execute_query

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

@router.post("/chat")
async def api_chat(request: ChatRequest):
    response = await execute_query(request.message)
    return {"reply": response}
