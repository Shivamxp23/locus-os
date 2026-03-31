import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.goals import router as goals_router
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.ai_gateway import router as ai_router
from app.api.v1.endpoints.telegram import router as telegram_router
from app.services.qdrant_service import ensure_collections

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_collections()
    except Exception:
        pass
    yield

app = FastAPI(title="Locus API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://locusapp.online", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(goals_router)
app.include_router(ai_router)
app.include_router(telegram_router)

@app.get("/")
async def root():
    return {"message": "Locus API is running.", "docs": "/docs"}
