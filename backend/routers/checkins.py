from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class MorningCheckin(BaseModel):
    energy: int
    mood: int
    sleep_quality: int
    stress: int
    intention: Optional[str] = None

class AfternoonCheckin(BaseModel):
    mood: int
    focus: int

class EveningCheckin(BaseModel):
    did_today: str
    avoided: Optional[str] = None
    avoided_reason: Optional[str] = None
    tomorrow_priority: str

class NightCheckin(BaseModel):
    reflection: Optional[str] = None
    sleep_intention: Optional[str] = None

def calculate_dcs(e: int, m: int, s: int, st: int) -> dict:
    dcs = round(((e + m + s) / 3) * (1 - st / 20), 2)
    dcs = max(0.0, min(10.0, dcs))
    if dcs <= 2.0: mode = "SURVIVAL"
    elif dcs <= 4.0: mode = "RECOVERY"
    elif dcs <= 6.0: mode = "NORMAL"
    elif dcs <= 8.0: mode = "DEEP_WORK"
    else: mode = "PEAK"
    return {"dcs": dcs, "mode": mode}

@router.post("/checkins/morning")
async def morning_checkin(data: MorningCheckin):
    result = calculate_dcs(data.energy, data.mood, data.sleep_quality, data.stress)
    return {"status": "ok", "dcs": result["dcs"], "mode": result["mode"]}

@router.post("/checkins/afternoon")
async def afternoon_checkin(data: AfternoonCheckin):
    return {"status": "ok", "message": "Afternoon check-in logged"}

@router.post("/checkins/evening")
async def evening_checkin(data: EveningCheckin):
    return {"status": "ok", "message": "Evening check-in logged"}

@router.post("/checkins/night")
async def night_checkin(data: NightCheckin):
    return {"status": "ok", "message": "Night check-in logged"}

@router.get("/checkins/today")
async def today_checkins():
    return {"checkins": [], "pending": ["morning", "afternoon", "evening", "night"]}
