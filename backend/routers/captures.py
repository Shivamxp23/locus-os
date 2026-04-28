# /opt/locus/backend/routers/captures.py — REAL implementation + Qdrant indexing

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import asyncpg
import os
import logging

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")
log = logging.getLogger(__name__)


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


class Capture(BaseModel):
    text: str
    source: Optional[str] = "pwa"


@router.post("/captures")
async def create_capture(capture: Capture):
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            INSERT INTO captures (user_id, text, source)
            VALUES ('shivam', $1, $2)
            RETURNING id, created_at
        """, capture.text, capture.source)

        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'capture', $1)
        """, f'{{"text": "{capture.text[:100]}", "source": "{capture.source}"}}')

        capture_id = str(row['id'])
    finally:
        await conn.close()

    # Index into Qdrant immediately (fire-and-forget)
    import asyncio
    asyncio.create_task(_index_capture(capture_id, capture.text, capture.source))

    return {"status": "ok", "message": "Captured ✓", "id": capture_id}


async def _index_capture(capture_id: str, text: str, source: str):
    """Async indexing — doesn't block the response."""
    try:
        from services.sync_layer import sync_capture
        result = await sync_capture(text=text, source=source)
        log.info(f"Capture {capture_id} synced: {result}")
    except Exception as e:
        log.warning(f"Capture sync failed (non-fatal): {e}")


@router.get("/captures")
async def get_captures(processed: bool = False, limit: int = 20):
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT id, text, source, processed, created_at
            FROM captures
            WHERE user_id = 'shivam' AND processed = $1
            ORDER BY created_at DESC LIMIT $2
        """, processed, limit)
        return {"captures": [dict(r) for r in rows]}
    finally:
        await conn.close()
