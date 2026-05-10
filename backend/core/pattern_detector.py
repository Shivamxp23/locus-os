import os
import json
import logging
from datetime import datetime
import httpx

log = logging.getLogger("locus-pattern-detector")

API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")
API_HEADERS = {"X-Service-Token": SERVICE_TOKEN}
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

PATTERN_PROMPT = """You are the Locus Multi-Horizon Pattern Detector.
Analyze the provided events and identify any behavioral patterns.
Horizons: 1 (6h), 2 (24h), 3 (7d), 4 (30d), 5 (all-time).

Return a strictly valid JSON list of identified patterns matching this schema:
[
  {
    "horizon": 1,
    "pattern_type": "string (e.g. avoidance, momentum, energy_crash)",
    "description": "Plain text description",
    "confidence": 0.0 to 1.0,
    "supporting_evidence": ["event descriptions"]
  }
]
If no clear patterns exist, return an empty list [].
"""

async def call_pattern_model(horizon: int, events: list) -> list:
    if not GROQ_API_KEY or not events:
        return []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": PATTERN_PROMPT},
                        {"role": "user", "content": f"Horizon {horizon} Data:\n{json.dumps(events)}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            if isinstance(result, dict):
                return result.get("patterns", [])
            return result
    except Exception as e:
        log.error(f"Pattern detection failed: {e}")
        return []

async def fetch_horizon_events(horizon: int) -> list:
    scope_map = {1: "last_6h", 2: "last_24h", 3: "last_7d", 4: "last_30d", 5: "all_time"}
    scope = scope_map.get(horizon, "last_7d")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_URL}/api/v1/context/postgres", params={"scope": scope}, headers=API_HEADERS)
            if r.status_code == 200:
                return r.json().get("events", [])
    except Exception:
        pass
    return []

async def detect_patterns_for_horizon(horizon: int):
    log.info(f"Running pattern detection for horizon {horizon}")
    events = await fetch_horizon_events(horizon)
    patterns = await call_pattern_model(horizon, events)

    if patterns:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{API_URL}/api/v1/context/patterns",
                    json={"patterns": patterns},
                    headers=API_HEADERS
                )
        except Exception as e:
            log.warning(f"Failed to save detected patterns: {e}")

async def run_all_horizons():
    for h in [1, 2, 3, 4, 5]:
        await detect_patterns_for_horizon(h)
