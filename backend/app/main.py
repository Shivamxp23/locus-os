import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

app = FastAPI(title="Locus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://locusapp.online", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def status():
    db_status = "disconnected"
    try:
        conn = await asyncpg.connect(os.getenv("DATABASE_URL", "").replace("+asyncpg", ""))
        await conn.fetchval("SELECT 1")
        await conn.close()
        db_status = "connected"
    except Exception:
        pass
    return {
        "status": "ok",
        "service": "locus-api",
        "version": "0.1.0",
        "postgres": db_status
    }

@app.get("/")
async def root():
    return {"message": "Locus API is running."}
