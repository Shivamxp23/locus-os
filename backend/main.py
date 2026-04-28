from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import logs, tasks, captures, vault, wiki, auth, checkins, context
from routers import goals, schedule, factions, analytics_data
from services.vault_jobs import (
    nightly_diff, weekly_synthesis,
    nightly_pattern_detection, exhaustion_check, dead_node_detection
)
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("locus-api")

app = FastAPI(title="Locus API", version="2.0.0")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple Auth Middleware ──
LOCUS_PASSWORD = os.getenv("LOCUS_PASSWORD", "")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")

# Paths that don't require auth
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Skip auth for health/docs and OPTIONS
    if path in PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    # Check for service token (internal services like telegram bot)
    token = request.headers.get("X-Service-Token", "")
    if token and token == SERVICE_TOKEN:
        return await call_next(request)

    # Check for password auth (PWA)
    auth_header = request.headers.get("X-Locus-Auth", "")
    if auth_header and auth_header == LOCUS_PASSWORD:
        return await call_next(request)

    # For now, allow all requests (remove this line for strict auth)
    # TODO: Enforce auth after PWA is updated to send credentials
    return await call_next(request)


# ── Routers ──
# Core
app.include_router(logs.router,     prefix="/api/v1")
app.include_router(tasks.router,    prefix="/api/v1")
app.include_router(captures.router, prefix="/api/v1")
app.include_router(vault.router,    prefix="/api/v1")
app.include_router(wiki.router,     prefix="/api/v1")
app.include_router(auth.router,     prefix="/api/v1")
app.include_router(checkins.router, prefix="/api/v1")
app.include_router(context.router,  prefix="/api/v1")

# New — Milestone 2+
app.include_router(goals.router,          prefix="/api/v1")
app.include_router(schedule.router,       prefix="/api/v1")
app.include_router(factions.router,       prefix="/api/v1")
app.include_router(analytics_data.router, prefix="/api/v1")
from routers import push, vector
app.include_router(push.router,           prefix="/api/v1")
app.include_router(vector.router,         prefix="/api/v1")

# ── Scheduler ──
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


@app.on_event("startup")
async def startup():
    log.info("Locus API v3.0 starting up — Brain Module Overhaul...")

    # ── Nightly Jobs ──
    scheduler.add_job(nightly_diff, "cron", hour=23, minute=30,
                      id="nightly_diff", replace_existing=True)

    scheduler.add_job(nightly_pattern_detection, "cron", hour=2, minute=30,
                      id="pattern_detection", replace_existing=True)

    scheduler.add_job(exhaustion_check, "cron", hour=3, minute=0,
                      id="exhaustion_check", replace_existing=True)

    # ── Weekly Jobs ──
    scheduler.add_job(weekly_synthesis, "cron", day_of_week="sun", hour=2,
                      id="weekly_synthesis", replace_existing=True)

    scheduler.add_job(dead_node_detection, "cron", day_of_week="sun", hour=6,
                      id="dead_node_detection", replace_existing=True)

    scheduler.start()
    log.info("APScheduler started with 5 jobs")


@app.get("/health")
async def health():
    sync_status = {}
    try:
        from services.sync_layer import sync_health
        sync_status = await sync_health()
    except Exception as e:
        sync_status = {"error": str(e)}

    return {
        "status": "ok",
        "version": "3.0.0",
        "jobs": [j.id for j in scheduler.get_jobs()],
        "sync": sync_status,
    }
