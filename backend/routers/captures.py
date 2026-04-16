# /opt/locus/backend/routers/captures.py — REAL implementation

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import asyncpg
import os

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")

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
    finally:
        await conn.close()
    
    return {"status": "ok", "message": "Captured ✓", "id": str(row['id'])}

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
