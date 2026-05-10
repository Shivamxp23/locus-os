import json

def encode_energy(energy: int, time_hhmm: str, faction: str) -> str:
    return f"{{e:{energy},t:{time_hhmm},f:{faction}}}"

def encode_task_done(short_name: str, duration_mins: int, quality: int) -> str:
    return f"{{✓:{short_name},dur:{duration_mins},q:{quality}}}"

def encode_task_deferred(short_name: str, deferral_count: int, reason: str) -> str:
    return f"{{→:{short_name},n:{deferral_count},r:{reason}}}"

def encode_mood(mood: int, note: str = "") -> str:
    words = " ".join(note.split()[:5])
    return f"{{m:{mood},note:{words}}}" if words else f"{{m:{mood}}}"

def encode_sleep(hours: float, quality: int) -> str:
    return f"{{s:{hours},q:{quality}}}"

def encode_food(desc: str, time_hhmm: str, energy_impact: str) -> str:
    return f"{{food:{desc},time:{time_hhmm},energy_impact:{energy_impact}}}"

def encode_faction_score(h: float, l: float, c: float, e: float) -> str:
    return f"{{H:{h:.1f},L:{l:.1f},C:{c:.1f},E:{e:.1f}}}"

def decode(shorthand_str: str) -> dict:
    try:
        shorthand_str = shorthand_str.strip("{}")
        parts = shorthand_str.split(",")
        result = {}
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                result[k] = v
        return result
    except Exception:
        return {}
