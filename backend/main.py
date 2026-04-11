from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routers import logs, tasks, captures, vault, wiki, auth, checkins, context  # context added
from services.vault_jobs import nightly_diff, weekly_synthesis
import os

app = FastAPI(title="Locus API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router,     prefix="/api/v1")
app.include_router(tasks.router,    prefix="/api/v1")
app.include_router(captures.router, prefix="/api/v1")
app.include_router(vault.router,    prefix="/api/v1")
app.include_router(wiki.router,     prefix="/api/v1")
app.include_router(auth.router,     prefix="/api/v1")
app.include_router(checkins.router, prefix="/api/v1")
app.include_router(context.router,  prefix="/api/v1")   # personality + learning loop

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    scheduler.add_job(nightly_diff,     "cron", hour=23, minute=30)
    scheduler.add_job(weekly_synthesis, "cron", day_of_week="sun", hour=2)
    scheduler.start()

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
