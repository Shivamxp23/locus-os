"""
state_engine.py — System 2.1: State Inference Pipeline

Maintains a CURRENT_STATE object in Redis (TTL 6 hours) that represents
Shivam's real-time psychological and operational state.

Triggered by:
- Every new PostgreSQL event write
- Every Telegram message received
- The inner loop (System 3)

The key output is the inferred_cause_chain — a genuine inference about
WHY Shivam is in his current state, citing specific data points.
"""

import os
import json
import logging
from datetime import datetime, timedelta
import httpx

from core.db import (
    pg_fetch, pg_fetchrow, pg_fetchval,
    redis_set_json, redis_get_json, pg_execute
)

log = logging.getLogger("locus-state-engine")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

INFERENCE_PROMPT = """You are the Locus State Inference Engine. You analyze raw data about Shivam and produce a precise assessment of his current state.

You are NOT talking to Shivam. You are generating internal system data about him.

IMPORTANT RULES:
- Every claim must be backed by data provided below. Never fabricate.
- The inferred_cause_chain must cite SPECIFIC data points (dates, values, events).
- If data is insufficient, say so. Don't guess.
- Be precise about temporal claims ("3 days" not "recently").

Return a strictly valid JSON object matching this schema:
{
  "timestamp": "ISO8601",
  "psychological_state": {
    "mood_trend": "rising|falling|stable",
    "mood_value": 0-10,
    "stress_indicators": ["list of active stressors"],
    "energy_level": 0-10,
    "energy_trend": "rising|falling|stable"
  },
  "operational_state": {
    "momentum": "building|stalling|blocked|recovering",
    "current_faction_focus": "health|leverage|craft|expression|none",
    "tasks_completed_today": 0,
    "tasks_deferred_today": 0,
    "deferral_rate_7d": 0.0,
    "last_meaningful_work_hours_ago": 0.0
  },
  "contextual_flags": {
    "exam_period": false,
    "exam_days_remaining": null,
    "recent_sleep_quality": 0-10,
    "last_meal_energy_impact": "+|-|0",
    "time_of_day_segment": "early_morning|morning|afternoon|evening|late_night|deep_night"
  },
  "behavioral_alerts": [
    {
      "type": "avoidance_pattern|momentum_loss|energy_mismatch|deadline_risk|faction_neglect",
      "description": "specific description with data citations",
      "severity": "low|medium|high",
      "evidence": ["specific event references"],
      "days_active": 0
    }
  ],
  "inferred_cause_chain": "A 3-5 sentence explanation of WHY Shivam is in this state, citing specific data points, historical patterns, and environmental factors."
}"""


def _get_time_segment() -> str:
    """Determine current time of day segment in IST."""
    hour = datetime.now().hour  # Assumes server is IST or adjust
    if 4 <= hour < 7:
        return "early_morning"
    elif 7 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    elif 21 <= hour < 24:
        return "late_night"
    else:
        return "deep_night"


async def _gather_context_data(trigger_event: dict = None) -> dict:
    """
    Gather all data needed for state inference from direct DB queries.
    No HTTP round-trips.
    """
    context = {
        "trigger": trigger_event,
        "time_segment": _get_time_segment(),
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # ── Recent daily logs (last 7 days) ──
        logs = await pg_fetch("""
            SELECT date, checkin_type, mood, energy, stress, focus,
                   sleep_hours, sleep_quality, dcs, mode,
                   did_today, avoided, avoided_reason
            FROM daily_logs
            WHERE date >= NOW() - INTERVAL '7 days'
            ORDER BY date DESC, created_at DESC
            LIMIT 30
        """)
        context["daily_logs"] = [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in row.items() if v is not None}
            for row in logs
        ]

        # ── Tasks completed today ──
        completed_today = await pg_fetchval("""
            SELECT count(*) FROM tasks
            WHERE status = 'done'
              AND completed_at >= CURRENT_DATE
        """)
        context["tasks_completed_today"] = completed_today or 0

        # ── Tasks deferred today ──
        deferred_today = await pg_fetchval("""
            SELECT count(*) FROM task_deferrals
            WHERE deferred_at >= CURRENT_DATE
        """)
        context["tasks_deferred_today"] = deferred_today or 0

        # ── 7-day deferral rate ──
        total_7d = await pg_fetchval("""
            SELECT count(*) FROM tasks
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        deferred_7d = await pg_fetchval("""
            SELECT count(*) FROM task_deferrals
            WHERE deferred_at >= NOW() - INTERVAL '7 days'
        """)
        context["deferral_rate_7d"] = (
            (deferred_7d / total_7d) if total_7d and total_7d > 0 else 0.0
        )

        # ── Last meaningful work ──
        last_done = await pg_fetchrow("""
            SELECT completed_at FROM tasks
            WHERE status = 'done' AND completed_at IS NOT NULL
            ORDER BY completed_at DESC LIMIT 1
        """)
        if last_done and last_done.get("completed_at"):
            delta = datetime.now(last_done["completed_at"].tzinfo) - last_done["completed_at"]
            context["last_meaningful_work_hours_ago"] = round(delta.total_seconds() / 3600, 1)
        else:
            context["last_meaningful_work_hours_ago"] = None

        # ── Frequently deferred tasks (avoidance signal) ──
        avoidance = await pg_fetch("""
            SELECT t.title, t.deferral_count, t.faction
            FROM tasks t
            WHERE t.deferral_count >= 3
            ORDER BY t.deferral_count DESC LIMIT 5
        """)
        context["chronic_deferrals"] = [dict(a) for a in avoidance]

        # ── Active detected patterns ──
        try:
            patterns = await pg_fetch("""
                SELECT pattern_type, description, confidence, horizon, days_active
                FROM detected_patterns
                WHERE status = 'active' AND confidence >= 0.6
                ORDER BY confidence DESC LIMIT 5
            """)
            context["active_patterns"] = [dict(p) for p in patterns]
        except Exception:
            context["active_patterns"] = []

        # ── Neo4j traits (lightweight) ──
        try:
            from services.neo4j_service import get_driver
            driver = await get_driver()
            async with driver.session() as s:
                r = await s.run(
                    "MATCH (p:Person {name:'Shivam'})-[:EXHIBITS_PATTERN]->(pat:Pattern) "
                    "RETURN pat.description AS desc, pat.strength AS str "
                    "ORDER BY pat.strength DESC LIMIT 3"
                )
                context["neo4j_patterns"] = [
                    {"description": rec["desc"], "strength": rec["str"]}
                    async for rec in r
                ]
        except Exception:
            context["neo4j_patterns"] = []

    except Exception as e:
        log.error(f"Context gathering failed: {e}")

    return context


async def infer_current_state(trigger_event: dict = None) -> dict:
    """
    Main entry point: gather context, call LLM, store in Redis.
    Returns the inferred CURRENT_STATE dict.
    """
    context_data = await _gather_context_data(trigger_event)

    if not GROQ_API_KEY:
        log.warning("No GROQ_API_KEY — cannot infer state")
        return {}

    # Check token budget
    from core.db import redis_get_int
    tokens_today = await redis_get_int("groq_tokens_today")
    if tokens_today > 25000:  # Conservative limit for free tier
        log.warning(f"Groq token budget tight ({tokens_today}), skipping state inference")
        # Return cached state if available
        cached = await redis_get_json("locus:current_state")
        return cached or {}

    try:
        # Truncate context to avoid sending too much
        context_str = json.dumps(context_data, default=str)
        if len(context_str) > 4000:
            context_str = context_str[:4000] + "..."

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": INFERENCE_PROMPT},
                        {"role": "user", "content": f"Current context data:\n{context_str}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": 800,
                }
            )
            r.raise_for_status()
            state = json.loads(r.json()["choices"][0]["message"]["content"])

            # Track token usage
            usage = r.json().get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            from core.db import redis_incr
            await redis_incr("groq_tokens_today", total_tokens)

    except Exception as e:
        log.error(f"State inference LLM call failed: {e}")
        return {}

    if state:
        # ── Store in Redis (6-hour TTL) ──
        await redis_set_json("locus:current_state", state, ttl_seconds=21600)

        # ── Snapshot to PostgreSQL (for historical tracking) ──
        try:
            await pg_execute("""
                INSERT INTO state_snapshots (user_id, snapshot_data)
                VALUES ('shivam', $1::jsonb)
            """, json.dumps(state, default=str))
        except Exception as e:
            log.warning(f"State snapshot save failed: {e}")

    return state
