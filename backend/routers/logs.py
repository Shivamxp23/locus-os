from fastapi import APIRouter
router = APIRouter()

@router.post("/log/morning")
async def morning_log(entry: dict):
    e, m, s, st = entry.get("e",5), entry.get("m",5), entry.get("s",5), entry.get("st",5)
    dcs = round(((e + m + s) / 3) * (1 - st / 20), 2)
    if dcs <= 2: mode = "SURVIVAL"
    elif dcs <= 4: mode = "RECOVERY"
    elif dcs <= 6: mode = "NORMAL"
    elif dcs <= 8: mode = "DEEP_WORK"
    else: mode = "PEAK"
    return {"status": "ok", "dcs": dcs, "mode": mode}
