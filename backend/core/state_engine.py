import os
import json
import logging
from datetime import datetime, timedelta
import httpx

log = logging.getLogger("locus-state-engine")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")
API_HEADERS = {"X-Service-Token": SERVICE_TOKEN}

INFERENCE_PROMPT = """You are the Locus Personal Inference Engine.
Based on the provided Postgres events, Neo4j patterns, recent Telegram messages, and environmental flags, infer Shivam's CURRENT psychological and operational state.

Return a strictly valid JSON object matching this schema:
{
  "timestamp": "ISO8601",
  "psychological_state": {
    "mood_trend": "rising|falling|stable",
    "mood_value": 0,
    "stress_indicators": ["list", "of", "strings"],
    "energy_level": 0,
    "energy_trend": "rising|falling|stable"
  },
  "operational_state": {
    "momentum": "building|stalling|blocked|recovering",
    "current_faction_focus": "string",
    "tasks_completed_today": 0,
    "tasks_deferred_today": 0,
    "deferral_rate_7d": 0.0,
    "last_meaningful_work_hours_ago": 0.0
  },
  "contextual_flags": {
    "exam_period": true|false,
    "exam_days_remaining": 0,
    "recent_sleep_quality": 0,
    "last_meal_energy_impact": "+|-|0",
    "time_of_day_segment": "early_morning|morning|afternoon|evening|late_night|deep_night"
  },
  "behavioral_alerts": [
    {
      "type": "string",
      "description": "string",
      "severity": "low|medium|high",
      "evidence": ["strings"],
      "days_active": 0
    }
  ],
  "inferred_cause_chain": "A 3-5 sentence plain text explanation of WHY Shivam is likely in this state right now, cross-referencing specific historical patterns, current events, sleep, and communication tone."
}
"""

async def call_inference_model(context_data: dict) -> dict:
    if not GROQ_API_KEY:
        log.warning("No GROQ API KEY for State Engine.")
        return {}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": INFERENCE_PROMPT},
                        {"role": "user", "content": f"Context Data:\n{json.dumps(context_data)}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2
                }
            )
            r.raise_for_status()
            return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:
        log.error(f"State inference failed: {e}")
        return {}

async def infer_current_state(trigger_event: dict = None) -> dict:
    events = []
    pathways = []
    try:
        async with httpx.AsyncClient() as client:
            r1 = await client.get(f"{API_URL}/api/v1/context/postgres", params={"scope": "last_24h"}, headers=API_HEADERS)
            if r1.status_code == 200:
                events = r1.json().get("events", [])
            r2 = await client.get(f"{API_URL}/api/v1/context/neo4j", headers=API_HEADERS)
            if r2.status_code == 200:
                pathways = r2.json().get("pathways", [])
    except Exception:
        pass

    context_data = {
        "recent_events": events,
        "recent_pathways": pathways,
        "trigger": trigger_event
    }

    state = await call_inference_model(context_data)

    if state:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{API_URL}/api/v1/context/state", json=state, headers=API_HEADERS)
        except Exception:
            pass

    return state
