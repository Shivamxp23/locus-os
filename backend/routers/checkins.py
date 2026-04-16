# /opt/locus/backend/routers/checkins.py
# REAL implementation — writes to PostgreSQL

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncpg
import os
from datetime import date, datetime

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

def calculate_dcs(e: int, m: int, s: int, st: int) -> dict:
    dcs = round(((e + m + s) / 3) * (1 - st / 20), 2)
    dcs = max(0.0, min(10.0, dcs))
    if dcs <= 2.0: mode = "SURVIVAL"
    elif dcs <= 4.0: mode = "RECOVERY"
    elif dcs <= 6.0: mode = "NORMAL"
    elif dcs <= 8.0: mode = "DEEP_WORK"
    else: mode = "PEAK"
    descriptions = {
        "SURVIVAL": "Protect non-negotiables only. No productive expectations.",
        "RECOVERY": "Gentle tasks only (D ≤ 4). Prefer Expression faction.",
        "NORMAL": "Standard operating. Balanced day possible.",
        "DEEP_WORK": "You are sharp. Use this for your hardest, highest-value work.",
        "PEAK": "Rare. Pull out the task you have been avoiding. Do not waste this."
    }
    return {"dcs": dcs, "mode": mode, "description": descriptions[mode]}

class MorningCheckin(BaseModel):
    energy: int = Field(..., ge=1, le=10)
    mood: int = Field(..., ge=1, le=10)
    sleep_quality: int = Field(..., ge=1, le=10)
    stress: int = Field(..., ge=1, le=10)
    time_available: Optional[float] = None
    intention: Optional[str] = None

class AfternoonCheckin(BaseModel):
    mood: int = Field(..., ge=1, le=10)
    focus: int = Field(..., ge=1, le=10)

class EveningCheckin(BaseModel):
    did_today: str
    avoided: Optional[str] = None
    avoided_reason: Optional[str] = None
    tomorrow_priority: str

class NightCheckin(BaseModel):
    reflection: Optional[str] = None
    sleep_intention: Optional[str] = None

@router.post("/checkins/morning")
async def morning_checkin(data: MorningCheckin):
    result = calculate_dcs(data.energy, data.mood, data.sleep_quality, data.stress)
    today = date.today()
    
    conn = await get_conn()
    try:
        # Upsert: if morning log exists for today, update it
        await conn.execute("""
            INSERT INTO daily_logs (
                user_id, date, checkin_type,
                energy, mood, sleep_quality, stress, dcs, mode,
                intention
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (user_id, date, checkin_type) DO UPDATE SET
                energy = EXCLUDED.energy,
                mood = EXCLUDED.mood,
                sleep_quality = EXCLUDED.sleep_quality,
                stress = EXCLUDED.stress,
                dcs = EXCLUDED.dcs,
                mode = EXCLUDED.mode,
                intention = EXCLUDED.intention
        """, 
        'shivam', today, 'morning',
        data.energy, data.mood, data.sleep_quality, data.stress,
        result["dcs"], result["mode"], data.intention)
        
        # Log behavioral event
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, 'shivam', 'morning_checkin', 
        f'{{"dcs": {result["dcs"]}, "mode": "{result["mode"]}", "energy": {data.energy}, "mood": {data.mood}}}')
        
    finally:
        await conn.close()
    
    return {
        "status": "ok",
        "dcs": result["dcs"],
        "mode": result["mode"],
        "description": result["description"]
    }

@router.post("/checkins/afternoon")
async def afternoon_checkin(data: AfternoonCheckin):
    today = date.today()
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO daily_logs (user_id, date, checkin_type, mood, focus)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, date, checkin_type) DO UPDATE SET
                mood = EXCLUDED.mood, focus = EXCLUDED.focus
        """, 'shivam', today, 'afternoon', data.mood, data.focus)
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, 'shivam', 'afternoon_checkin',
        f'{{"mood": {data.mood}, "focus": {data.focus}}}')
    finally:
        await conn.close()
    
    return {"status": "ok", "message": "Afternoon check-in logged"}

@router.post("/checkins/evening")
async def evening_checkin(data: EveningCheckin):
    today = date.today()
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO daily_logs (
                user_id, date, checkin_type,
                did_today, avoided, avoided_reason, tomorrow_priority
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, date, checkin_type) DO UPDATE SET
                did_today = EXCLUDED.did_today,
                avoided = EXCLUDED.avoided,
                avoided_reason = EXCLUDED.avoided_reason,
                tomorrow_priority = EXCLUDED.tomorrow_priority
        """, 'shivam', today, 'evening',
        data.did_today, data.avoided, data.avoided_reason, data.tomorrow_priority)
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, 'shivam', 'evening_checkin',
        f'{{"did_today": "{data.did_today[:100]}", "avoided": "{(data.avoided or "")[:100]}"}}')
    finally:
        await conn.close()
    
    return {"status": "ok", "message": "Evening check-in logged"}

@router.post("/checkins/night")
async def night_checkin(data: NightCheckin):
    today = date.today()
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO daily_logs (user_id, date, checkin_type, reflection, sleep_intention)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, date, checkin_type) DO UPDATE SET
                reflection = EXCLUDED.reflection,
                sleep_intention = EXCLUDED.sleep_intention
        """, 'shivam', today, 'night', data.reflection, data.sleep_intention)
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, 'shivam', 'night_checkin', '{"logged": true}')
    finally:
        await conn.close()
    
    return {"status": "ok", "message": "Night check-in logged"}

@router.get("/checkins/today")
async def today_checkins():
    today = date.today()
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT checkin_type, dcs, mode, energy, mood, sleep_quality, stress,
                   intention, did_today, avoided, tomorrow_priority, reflection
            FROM daily_logs
            WHERE user_id = 'shivam' AND date = $1
        """, today)
        
        done = [r['checkin_type'] for r in rows]
        pending = [t for t in ['morning', 'afternoon', 'evening', 'night'] if t not in done]
        
        checkins = {}
        for r in rows:
            checkins[r['checkin_type']] = dict(r)
        
        return {
            "date": str(today),
            "checkins": checkins,
            "pending": pending,
            "dcs": checkins.get('morning', {}).get('dcs'),
            "mode": checkins.get('morning', {}).get('mode')
        }
    finally:
        await conn.close()
