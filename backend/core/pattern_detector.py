"""
pattern_detector.py — System 2.2: Multi-Horizon Pattern Detector

Detects behavioral patterns across FIVE time horizons simultaneously.
Runs every 6 hours via APScheduler.

Patterns with confidence > 0.75 and confirmation_count > 2 are promoted
to PERSISTENT_PATTERNS and included in the User Identity Layer.
"""

import os
import json
import logging
import uuid
from datetime import datetime
import httpx

from core.db import pg_fetch, pg_fetchrow, pg_fetchval, pg_execute

log = logging.getLogger("locus-pattern-detector")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HORIZON_MAP = {
    1: ("Last 6 hours (acute state)", "6 hours"),
    2: ("Last 24 hours (daily pattern)", "24 hours"),
    3: ("Last 7 days (weekly pattern)", "7 days"),
    4: ("Last 30 days (monthly pattern)", "30 days"),
    5: ("All time (identity pattern)", "3650 days"),
}

PATTERN_PROMPT = """You are the Locus Multi-Horizon Pattern Detector. You analyze behavioral data and identify genuine patterns.

Horizon being analyzed: {horizon_name}

You are NOT talking to Shivam. You are generating internal pattern data.

RULES:
- Only identify patterns supported by the data. Never fabricate.
- Each pattern must cite specific data points as evidence.
- Confidence = 0.0 (speculation) to 1.0 (certain, multiple confirmations).
- Be specific. "Low energy" is not a pattern. "Energy drops below 4/10 consistently between 14:00-16:00 on weekdays" IS a pattern.

PATTERN TYPES: avoidance, momentum, energy, mood, faction_neglect, goal_drift,
               exam_behavior, creative_burst, sleep_impact, deferral_cascade,
               time_of_day_performance, stress_response

Return a strictly valid JSON object:
{
  "patterns": [
    {
      "horizon": HORIZON_NUMBER,
      "pattern_type": "string",
      "description": "Specific description with data citations",
      "confidence": 0.0 to 1.0,
      "supporting_evidence": ["specific event/data references"]
    }
  ]
}

If no clear patterns exist, return: {"patterns": []}
"""


async def _fetch_horizon_data(horizon: int) -> dict:
    """Fetch data for a specific time horizon directly from PostgreSQL."""
    interval = HORIZON_MAP[horizon][1]
    data = {}

    try:
        # Daily logs
        logs = await pg_fetch("""
            SELECT date, checkin_type, mood, energy, stress, focus,
                   sleep_hours, sleep_quality, dcs, mode,
                   did_today, avoided, avoided_reason
            FROM daily_logs
            WHERE date >= NOW() - $1::interval
            ORDER BY date DESC
        """, interval)
        data["daily_logs"] = [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in row.items() if v is not None}
            for row in logs
        ]

        # Tasks and deferrals
        tasks = await pg_fetch("""
            SELECT title, status, faction, deferral_count, completed_at,
                   created_at, estimated_hours, actual_hours
            FROM tasks
            WHERE created_at >= NOW() - $1::interval
            ORDER BY created_at DESC
            LIMIT 30
        """, interval)
        data["tasks"] = [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in row.items() if v is not None}
            for row in tasks
        ]

        # Behavioral events
        events = await pg_fetch("""
            SELECT event_type, data, created_at
            FROM behavioral_events
            WHERE created_at >= NOW() - $1::interval
            ORDER BY created_at DESC
            LIMIT 20
        """, interval)
        data["behavioral_events"] = [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in row.items() if v is not None}
            for row in events
        ]

        # Faction stats
        factions = await pg_fetch("""
            SELECT faction, actual_hours, target_hours, week_start
            FROM faction_stats
            WHERE week_start >= NOW() - $1::interval
            ORDER BY week_start DESC
        """, interval)
        data["faction_stats"] = [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in row.items() if v is not None}
            for row in factions
        ]

    except Exception as e:
        log.error(f"Horizon {horizon} data fetch failed: {e}")

    return data


async def _detect_for_horizon(horizon: int) -> list:
    """Run pattern detection for a single horizon."""
    horizon_name = HORIZON_MAP[horizon][0]
    data = await _fetch_horizon_data(horizon)

    if not any(data.values()):
        log.info(f"Horizon {horizon}: no data available")
        return []

    if not GROQ_API_KEY:
        return []

    # Check token budget
    from core.db import redis_get_int, redis_incr
    tokens_today = await redis_get_int("groq_tokens_today")
    if tokens_today > 25000:
        log.warning(f"Skipping horizon {horizon} — token budget tight")
        return []

    try:
        prompt = PATTERN_PROMPT.format(horizon_name=horizon_name)
        data_str = json.dumps(data, default=str)
        if len(data_str) > 3000:
            data_str = data_str[:3000] + "..."

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Horizon {horizon} data:\n{data_str}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 500,
                }
            )
            r.raise_for_status()

            # Track tokens
            usage = r.json().get("usage", {})
            await redis_incr("groq_tokens_today", usage.get("total_tokens", 0))

            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            patterns = result.get("patterns", [])

            # Ensure horizon is set correctly
            for p in patterns:
                p["horizon"] = horizon

            return patterns

    except Exception as e:
        log.error(f"Pattern detection horizon {horizon} failed: {e}")
        return []


async def _save_patterns(patterns: list):
    """
    Save detected patterns to PostgreSQL.
    If a similar pattern already exists, increment confirmation_count.
    """
    for p in patterns:
        try:
            # Check if a similar pattern already exists (same type + similar description)
            existing = await pg_fetchrow("""
                SELECT id, confirmation_count, confidence
                FROM detected_patterns
                WHERE pattern_type = $1
                  AND horizon = $2
                  AND status = 'active'
                  AND description ILIKE '%' || $3 || '%'
                LIMIT 1
            """, p.get("pattern_type", "unknown"),
                p.get("horizon", 3),
                p.get("description", "")[:50])

            if existing:
                # Update existing pattern
                new_confidence = min(1.0, (
                    existing["confidence"] * 0.7 + p.get("confidence", 0.5) * 0.3
                ))
                await pg_execute("""
                    UPDATE detected_patterns
                    SET last_confirmed_at = NOW(),
                        confirmation_count = confirmation_count + 1,
                        confidence = $1,
                        supporting_event_ids = supporting_event_ids || $2::jsonb
                    WHERE id = $3
                """, new_confidence,
                    json.dumps(p.get("supporting_evidence", [])),
                    existing["id"])
            else:
                # Insert new pattern
                await pg_execute("""
                    INSERT INTO detected_patterns
                        (user_id, horizon, pattern_type, description, confidence,
                         supporting_event_ids)
                    VALUES ('shivam', $1, $2, $3, $4, $5::jsonb)
                """, p.get("horizon", 3),
                    p.get("pattern_type", "unknown"),
                    p.get("description", ""),
                    p.get("confidence", 0.5),
                    json.dumps(p.get("supporting_evidence", [])))

        except Exception as e:
            log.warning(f"Pattern save failed: {e}")


async def _promote_persistent_patterns():
    """
    Patterns with confidence > 0.75 and confirmation_count > 2 update
    the user_identity table's known_behavioral_tendencies using a
    weighted rolling average.
    """
    try:
        persistent = await pg_fetch("""
            SELECT pattern_type, description, confidence
            FROM detected_patterns
            WHERE status = 'active'
              AND confidence > 0.75
              AND confirmation_count > 2
        """)

        if not persistent:
            return

        # Fetch current identity
        identity = await pg_fetchrow("""
            SELECT known_behavioral_tendencies, peak_performance_windows
            FROM user_identity
            WHERE user_id = 'shivam'
        """)

        if not identity:
            return

        tendencies = identity.get("known_behavioral_tendencies") or {}
        if isinstance(tendencies, str):
            tendencies = json.loads(tendencies)

        # Update tendencies with persistent patterns
        for p in persistent:
            ptype = p["pattern_type"]
            new_conf = p["confidence"]
            old_conf = tendencies.get(ptype, 0.5)
            # Weighted rolling average: 70% old, 30% new
            tendencies[ptype] = round(old_conf * 0.7 + new_conf * 0.3, 3)

        await pg_execute("""
            UPDATE user_identity
            SET known_behavioral_tendencies = $1::jsonb,
                last_updated = NOW(),
                update_source = 'ai_inference'
            WHERE user_id = 'shivam'
        """, json.dumps(tendencies))

        log.info(f"Promoted {len(persistent)} patterns to user identity")

    except Exception as e:
        log.warning(f"Pattern promotion failed: {e}")


async def run_all_horizons():
    """
    Main entry point. Runs all 5 horizons and saves results.
    Called every 6 hours by APScheduler.
    """
    log.info("Running multi-horizon pattern detection...")

    all_patterns = []
    for horizon in [1, 2, 3, 4, 5]:
        patterns = await _detect_for_horizon(horizon)
        if patterns:
            all_patterns.extend(patterns)
            log.info(f"Horizon {horizon}: detected {len(patterns)} patterns")

    if all_patterns:
        await _save_patterns(all_patterns)

    # Promote confirmed patterns to identity
    await _promote_persistent_patterns()

    log.info(f"Pattern detection complete: {len(all_patterns)} total patterns")
