"""
shorthand.py — System 1.4: LOCUS_SHORTHAND Compression Schema

Compresses personal data into dense token-efficient shorthand for
context windows. ~75% token reduction.

BEFORE (47 tokens):
"User logged energy 6/10 at 22:30 while working on craft faction,
deferred Locus coding task for the 3rd time because they felt tired,
mood was 4/10"

AFTER (12 tokens):
{e:6,t:2230,f:craft} {→:locus-code,n:3,r:tired} {m:4}
"""

# ── Encoders ──────────────────────────────────────────────────


def encode_energy(energy: int, time_hhmm: str, faction: str) -> str:
    return f"{{e:{energy},t:{time_hhmm},f:{faction}}}"


def encode_task_done(short_name: str, duration_mins: int, quality: int) -> str:
    return f"{{✓:{short_name},dur:{duration_mins},q:{quality}}}"


def encode_task_deferred(short_name: str, deferral_count: int, reason: str) -> str:
    # Normalize reason to code
    reason_codes = {
        "busy": "busy", "tired": "tired", "blocked": "blocked",
        "forgot": "forgot", "impulse": "impulse", "unclear": "unclear",
        "procrastination": "impulse", "lazy": "tired", "overwhelmed": "busy",
    }
    code = reason_codes.get(reason.lower().strip(), reason[:8] if reason else "unknown")
    return f"{{→:{short_name[:15]},n:{deferral_count},r:{code}}}"


def encode_mood(mood: int, note: str = "") -> str:
    words = " ".join(note.split()[:5])
    return f"{{m:{mood},note:{words}}}" if words else f"{{m:{mood}}}"


def encode_sleep(hours: float, quality: int) -> str:
    return f"{{s:{hours},q:{quality}}}"


def encode_food(desc: str, time_hhmm: str, energy_impact: str) -> str:
    return f"{{food:{desc[:20]},time:{time_hhmm},energy_impact:{energy_impact}}}"


def encode_faction_score(h: float, l: float, c: float, e: float) -> str:
    return f"{{H:{h:.1f},L:{l:.1f},C:{c:.1f},E:{e:.1f}}}"


def encode_daily_log(log_data: dict) -> str:
    """Compress a daily_log row into shorthand."""
    parts = []

    if log_data.get("mood"):
        parts.append(f"m:{log_data['mood']}")
    if log_data.get("energy"):
        parts.append(f"e:{log_data['energy']}")
    if log_data.get("stress"):
        parts.append(f"str:{log_data['stress']}")
    if log_data.get("sleep_hours"):
        parts.append(f"s:{log_data['sleep_hours']}")
    if log_data.get("sleep_quality"):
        parts.append(f"sq:{log_data['sleep_quality']}")
    if log_data.get("dcs"):
        parts.append(f"dcs:{log_data['dcs']}")
    if log_data.get("mode"):
        parts.append(f"mode:{log_data['mode']}")
    if log_data.get("checkin_type"):
        parts.append(f"@{log_data['checkin_type']}")

    date_str = str(log_data.get("date", ""))
    if date_str:
        parts.insert(0, date_str[-5:])  # e.g. "05-12"

    return "{" + ",".join(parts) + "}"


def encode_task(task_data: dict) -> str:
    """Compress a task row into shorthand."""
    status_map = {"pending": "⏳", "in_progress": "🔄", "done": "✓", "deferred": "→", "killed": "✗"}
    status = status_map.get(task_data.get("status", ""), "?")
    title = task_data.get("title", "?")[:20]
    faction = (task_data.get("faction", "") or "")[:3]
    tws = task_data.get("tws", "")

    parts = [f"{status}:{title}"]
    if faction:
        parts.append(f"f:{faction}")
    if tws:
        parts.append(f"tws:{tws}")
    if task_data.get("deferral_count", 0) > 0:
        parts.append(f"def:{task_data['deferral_count']}")

    return "{" + ",".join(parts) + "}"


# ── Decoder ──────────────────────────────────────────────────


def decode(shorthand_str: str) -> dict:
    """Decode a shorthand string back to a dict."""
    try:
        shorthand_str = shorthand_str.strip("{}")
        parts = shorthand_str.split(",")
        result = {}
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                result[k.strip()] = v.strip()
        return result
    except Exception:
        return {}


# ── Schema Description (for LLM system prompt) ──────────────

SHORTHAND_SCHEMA_PROMPT = """
LOCUS_SHORTHAND FORMAT (compressed personal data):
- Daily log: {date,m:MOOD,e:ENERGY,str:STRESS,s:SLEEP_H,sq:SLEEP_Q,dcs:DCS,mode:MODE,@CHECKIN_TYPE}
- Task done: {✓:TASK_NAME,dur:MINS,q:QUALITY_1-10}
- Task deferred: {→:TASK_NAME,n:DEFERRAL_COUNT,r:REASON_CODE}
  Reason codes: busy|tired|blocked|forgot|impulse|unclear
- Task pending: {⏳:TASK_NAME,f:FACTION,tws:TWS_SCORE,def:DEFERRAL_COUNT}
- Mood: {m:VALUE,note:MAX_5_WORDS}
- Sleep: {s:HOURS,q:QUALITY_1-10}
- Food: {food:DESC,time:HHMM,energy_impact:+/-/0}
- Faction scores: {H:HEALTH,L:LEVERAGE,C:CRAFT,E:EXPRESSION}
"""
