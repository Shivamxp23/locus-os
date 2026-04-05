from fastapi import APIRouter
from datetime import datetime
import httpx
import asyncpg
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(tags=["system"])


@router.get("/status")
async def status():
    db_status = "disconnected"
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
        await conn.fetchval("SELECT 1")
        await conn.close()
        db_status = "connected"
    except Exception:
        pass
    return {"status": "ok", "service": "locus-api", "version": "0.1.0", "postgres": db_status}


async def _run_health_checks() -> dict:
    result = {}

    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
        await conn.fetchval("SELECT 1")
        await conn.close()
        result["postgres"] = "ok"
    except Exception as e:
        result["postgres"] = f"error: {str(e)}"

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        result["redis"] = "ok"
    except Exception:
        result["redis"] = "error"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags", timeout=5)
            result["ollama"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        result["ollama"] = "error"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.QDRANT_URL}/healthz", timeout=5)
            result["qdrant"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        result["qdrant"] = "error"

    return result


@router.get("/health")
@router.get("/api/system/health")
async def health():
    result = await _run_health_checks()
    all_ok = all(v == "ok" for v in result.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "services": result,
        "timestamp": datetime.utcnow().isoformat()
    }
