"""
Locus Backend — Stub FastAPI Application
Phase 1: Health check + audit endpoint for OpenClaw integration testing.

All business logic will be added in Phase 2+.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("locus")

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Locus API",
    description="Personal Cognitive Operating System — Backend API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be locked to locusapp.online in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────
class AuditEvent(BaseModel):
    event_type: str
    tool_name: str
    timestamp: str
    input_payload: Optional[Any] = None
    response_status: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class MorningLogRequest(BaseModel):
    energy: int
    mood: int
    sleep: int
    stress: int
    time_available: float


class TaskRequest(BaseModel):
    action: str
    title: Optional[str] = None
    quality: Optional[int] = None
    actual_time: Optional[float] = None
    reason: Optional[str] = None


class SearchRequest(BaseModel):
    query: str


class CaptureRequest(BaseModel):
    content: str
    type: str = "note"


class JobTriggerRequest(BaseModel):
    job: str


# ── Health ───────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "locus-api",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Audit Endpoint (Modification 3 receiver) ────────────────────
@app.post("/api/v1/internal/audit/openclaw")
async def receive_audit(event: AuditEvent):
    logger.info(
        f"[AUDIT] {event.event_type} | tool={event.tool_name} | "
        f"status={event.response_status} | duration={event.duration_ms}ms"
    )
    return {"received": True, "event_type": event.event_type}


# ── Morning Log (stub) ──────────────────────────────────────────
@app.post("/api/v1/log/morning")
async def log_morning(req: MorningLogRequest):
    logger.info(
        f"[MORNING] E={req.energy} M={req.mood} S={req.sleep} "
        f"ST={req.stress} T={req.time_available}"
    )
    # Stub response — real DCS calculation comes in Phase 2
    return {
        "status": "logged",
        "dcs_score": 7.0,
        "mode": "Focus",
        "top_tasks": [
            "Complete Phase 1 hardening",
            "Review architecture doc",
            "Set up Docker on VM",
        ],
    }


# ── Task Management (stub) ──────────────────────────────────────
@app.post("/api/v1/tasks/{action}")
async def manage_task(action: str, req: TaskRequest):
    logger.info(f"[TASK] action={action} title={req.title}")
    return {
        "status": "ok",
        "action": action,
        "message": f"Task {action} processed (stub)",
    }


# ── Schedule Query (stub) ───────────────────────────────────────
@app.get("/api/v1/schedule/today")
async def schedule_today():
    logger.info("[QUERY] schedule/today requested")
    return {
        "status": "ok",
        "tasks": [
            {"title": "Phase 1 — OpenClaw Hardening", "priority": 1, "estimated_hours": 2},
            {"title": "Review architecture", "priority": 2, "estimated_hours": 1},
        ],
        "mode": "Focus",
        "dcs_score": 7.0,
    }


# ── Voice Note (stub) ───────────────────────────────────────────
@app.post("/api/v1/log/voice")
async def log_voice(request: Request):
    body = await request.body()
    logger.info(f"[VOICE] received {len(body)} bytes")
    return {"status": "received", "bytes": len(body), "message": "Voice note stub processed"}


# ── Appledore Search (stub) ─────────────────────────────────────
@app.post("/api/v1/appledore/search")
async def search_appledore(req: SearchRequest):
    logger.info(f"[APPLEDORE] search query: {req.query}")
    return {
        "status": "ok",
        "results": [
            {"file": "daily/2026-04-05.md", "snippet": f"Stub result for: {req.query}"},
        ],
    }


# ── Capture (stub) ──────────────────────────────────────────────
@app.post("/api/v1/log/capture")
async def log_capture(req: CaptureRequest):
    logger.info(f"[CAPTURE] type={req.type} content={req.content[:50]}...")
    return {"status": "captured", "type": req.type}


# ── Cron Job Trigger (stub) ─────────────────────────────────────
@app.post("/api/v1/internal/jobs/trigger")
async def trigger_job(req: JobTriggerRequest):
    logger.info(f"[CRON] job triggered: {req.job}")
    return {"status": "triggered", "job": req.job}
