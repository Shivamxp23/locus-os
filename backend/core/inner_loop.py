"""
inner_loop.py — System 3: Proactive Inner Loop

A persistent background reasoning process that runs independently of
user input. This makes Locus think without being asked.

Schedule:
- Every 90 minutes (07:00–00:00 IST): standard pass
- 03:00 IST: nightly deep synthesis
- 03:30 IST Sunday: weekly decay of Neo4j edge weights
- 08:00 IST: morning briefing
"""

import os
import json
import logging
from datetime import datetime
import httpx

from core.db import (
    pg_fetch, pg_fetchrow, pg_fetchval, pg_execute,
    redis_get_json, redis_set_json, redis_get_int, redis_incr
)

log = logging.getLogger("locus-inner-loop")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID")

# ── Groq free tier limits ──
# ~14,400 requests/day, ~6000 tokens/min for 8b, ~6000 tokens/min for 70b
GROQ_DAILY_TOKEN_LIMIT = 28000  # Conservative budget (leave room for user queries)
GROQ_PAUSE_THRESHOLD = int(GROQ_DAILY_TOKEN_LIMIT * 0.8)  # 80%

INNER_LOOP_PROMPT = """You are Locus's internal reasoning process. You are NOT talking to Shivam. You are thinking about Shivam.

Your job: generate 0-2 specific, evidence-based observations about what you are noticing in his data right now.

Rules:
- Be specific. Cite data points (dates, values, counts). Not generic advice.
- If you have nothing meaningful, return empty observations array.
- Never fabricate. If the data doesn't support it, don't say it.
- You know Shivam: direct, no sycophancy, push-back welcome, technically sharp, filmmaker + developer.
- Consider: time of day, exam periods, sleep quality, deferral patterns, energy trends.
- An observation is ONLY worth surfacing if it reveals something non-obvious.

Current context from the system:
{context}

Return JSON:
{
  "observations": [
    {
      "text": "specific observation with data citations",
      "confidence": 0.0 to 1.0,
      "should_surface": true or false,
      "surface_timing": "now|morning_brief|hold"
    }
  ]
}"""

NIGHTLY_SYNTHESIS_PROMPT = """You are Locus's nightly deep synthesis engine. You analyze today's full data and generate an honest assessment.

You are NOT talking to Shivam. You are writing an internal daily report about him.

Rules:
- Be specific and cite data points.
- Don't fabricate. If today was unremarkable, say so.
- Be direct. No filler. No generic motivation.

Today's data:
{context}

Generate:
1. end_of_day_synthesis: What kind of day was it really? (2-3 sentences, cite data)
2. key_insight: One thing Shivam might not have noticed about today (1-2 sentences)
3. recommended_framing: How should he approach tomorrow based on today? (1-2 sentences)

Return JSON:
{
  "end_of_day_synthesis": "string",
  "key_insight": "string",
  "recommended_framing": "string"
}"""

MORNING_BRIEF_PROMPT = """You are Locus generating Shivam's morning briefing. Be direct, under 200 words.

Data:
{context}

Format a concise morning message that includes:
1. Last night's synthesis insight (if available)
2. Queued observations from inner loop
3. Top 3 recommended tasks for today (based on faction balance, energy patterns, deadlines)
4. One behavioral observation from detected patterns

Style: Direct. No fluff. No "Good morning!" bullshit. Shivam hates sycophancy.
Return plain text (not JSON). Maximum 200 words."""


async def _send_telegram(text: str, parse_mode: str = "Markdown"):
    """Send a message to Shivam via Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_OWNER_ID:
        log.warning("Telegram credentials not set")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Add feedback buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "👍", "callback_data": f"fb_up_inner_{int(datetime.now().timestamp())}"},
                        {"text": "👎", "callback_data": f"fb_down_inner_{int(datetime.now().timestamp())}"},
                    ]
                ]
            }
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_OWNER_ID,
                    "text": text,
                    "parse_mode": parse_mode,
                    "reply_markup": keyboard,
                }
            )
    except Exception as e:
        log.error(f"Telegram send failed: {e}")


async def _check_token_budget() -> bool:
    """Returns True if we have token budget remaining."""
    tokens_today = await redis_get_int("groq_tokens_today")
    if tokens_today > GROQ_PAUSE_THRESHOLD:
        log.warning(f"Token budget exceeded ({tokens_today}/{GROQ_DAILY_TOKEN_LIMIT})")
        await _send_telegram(
            "⚠️ *Locus inner loop paused* — approaching daily Groq token limit "
            f"({tokens_today} tokens used)."
        )
        return False
    return True


async def _check_similarity_suppress(observation_text: str) -> bool:
    """
    Check if this observation is too similar to something said in last 6h.
    Returns True if should be suppressed.
    """
    try:
        from services.qdrant_service import get_embedding
        vec = await get_embedding(observation_text)
        if not vec:
            return False

        # Search recent conversation history in Qdrant
        async with httpx.AsyncClient(timeout=5) as client:
            qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
            r = await client.post(
                f"{qdrant_url}/collections/locus_vault/points/search",
                json={"vector": vec, "limit": 3, "with_payload": True, "score_threshold": 0.85}
            )
            if r.status_code == 200:
                results = r.json().get("result", [])
                for pt in results:
                    # Check if this is from last 6 hours
                    payload = pt.get("payload", {})
                    modified = payload.get("file_modified_at", "")
                    if modified:
                        try:
                            mod_time = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                            if (datetime.now(mod_time.tzinfo) - mod_time).total_seconds() < 21600:
                                return True  # Suppress — too similar to recent content
                        except Exception:
                            pass
    except Exception:
        pass

    return False


async def run_standard_pass():
    """
    Standard 90-minute inner loop pass.
    Fetches current state + recent events, generates observations,
    surfaces to Telegram if warranted.
    """
    log.info("Running standard 90-min inner loop pass")

    # Check time of day (only run 07:00–00:00 IST)
    hour = datetime.now().hour
    if hour < 7:
        log.info("Skipping inner loop — outside active hours (07:00–00:00)")
        return

    if not await _check_token_budget():
        return

    # ── Gather context ──
    state = await redis_get_json("locus:current_state")
    if not state:
        # Trigger fresh state inference
        from core.state_engine import infer_current_state
        state = await infer_current_state()

    recent_events = await pg_fetch("""
        SELECT date, checkin_type, mood, energy, did_today, avoided
        FROM daily_logs
        WHERE created_at >= NOW() - INTERVAL '6 hours'
        ORDER BY created_at DESC LIMIT 5
    """)

    recent_patterns = []
    try:
        recent_patterns = await pg_fetch("""
            SELECT pattern_type, description, confidence
            FROM detected_patterns
            WHERE status = 'active'
              AND last_confirmed_at >= NOW() - INTERVAL '24 hours'
            ORDER BY confidence DESC LIMIT 3
        """)
    except Exception:
        pass

    context_data = {
        "current_state": state,
        "recent_events": [
            {k: (str(v) if hasattr(v, 'isoformat') else v)
             for k, v in e.items() if v is not None}
            for e in recent_events
        ],
        "recent_patterns": [dict(p) for p in recent_patterns],
        "current_time": datetime.now().isoformat(),
    }

    context_str = json.dumps(context_data, default=str)
    if len(context_str) > 2500:
        context_str = context_str[:2500] + "..."

    if not GROQ_API_KEY:
        return

    try:
        prompt = INNER_LOOP_PROMPT.format(context=context_str)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                    "max_tokens": 400,
                }
            )
            r.raise_for_status()

            # Track tokens
            usage = r.json().get("usage", {})
            await redis_incr("groq_tokens_today", usage.get("total_tokens", 0))

            result = json.loads(r.json()["choices"][0]["message"]["content"])
            observations = result.get("observations", [])

            for obs in observations:
                if not obs.get("should_surface"):
                    continue

                timing = obs.get("surface_timing", "hold")
                confidence = obs.get("confidence", 0)
                text = obs.get("text", "")

                if timing == "now" and confidence > 0.65:
                    # Check suppression
                    if await _check_similarity_suppress(text):
                        log.info(f"Suppressed observation (similar to recent): {text[:50]}")
                        continue
                    await _send_telegram(f"💡 {text}")

                elif timing == "morning_brief":
                    # Queue for morning briefing
                    try:
                        await pg_execute("""
                            INSERT INTO morning_briefing_queue
                                (user_id, observation_text, confidence, source)
                            VALUES ('shivam', $1, $2, 'inner_loop')
                        """, text, confidence)
                    except Exception as e:
                        log.warning(f"Morning brief queue failed: {e}")

                elif timing == "hold":
                    # Store as detected pattern for confirmation
                    try:
                        await pg_execute("""
                            INSERT INTO detected_patterns
                                (user_id, horizon, pattern_type, description, confidence)
                            VALUES ('shivam', 1, 'inner_loop_observation', $1, $2)
                        """, text, confidence)
                    except Exception as e:
                        log.warning(f"Pattern hold save failed: {e}")

    except Exception as e:
        log.error(f"Inner loop pass failed: {e}")


async def run_nightly_synthesis():
    """
    Deep synthesis at 03:00 IST.
    Uses 70b-versatile (or Gemini 2.5 Pro on Sundays).
    """
    log.info("Running nightly deep synthesis")

    if not await _check_token_budget():
        return

    # Gather full day's data
    try:
        daily_events = await pg_fetch("""
            SELECT date, checkin_type, mood, energy, stress, sleep_hours,
                   sleep_quality, dcs, mode, did_today, avoided, avoided_reason
            FROM daily_logs
            WHERE date >= CURRENT_DATE - 1
            ORDER BY date DESC, created_at DESC
        """)

        patterns_today = await pg_fetch("""
            SELECT pattern_type, description, confidence
            FROM detected_patterns
            WHERE last_confirmed_at >= CURRENT_DATE - 1
              AND status = 'active'
        """)

        # State snapshots from last 24h
        snapshots = await pg_fetch("""
            SELECT snapshot_data, created_at
            FROM state_snapshots
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 4
        """)

        context_data = {
            "daily_events": [
                {k: (str(v) if hasattr(v, 'isoformat') else v)
                 for k, v in e.items() if v is not None}
                for e in daily_events
            ],
            "patterns_today": [dict(p) for p in patterns_today],
            "state_snapshots": [
                {"data": s["snapshot_data"], "at": str(s["created_at"])}
                for s in snapshots
            ],
        }

    except Exception as e:
        log.error(f"Nightly synthesis data fetch failed: {e}")
        return

    context_str = json.dumps(context_data, default=str)
    if len(context_str) > 4000:
        context_str = context_str[:4000] + "..."

    # Determine model: Sunday → Gemini, otherwise → 70b
    is_sunday = datetime.now().weekday() == 6
    prompt = NIGHTLY_SYNTHESIS_PROMPT.format(context=context_str)

    try:
        if is_sunday and GEMINI_API_KEY:
            # Use Gemini 2.5 Pro for Sunday synthesis
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.3,
                        }
                    }
                )
                r.raise_for_status()
                content = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(content)
                model_used = "gemini-2.5-pro"
        else:
            # Use Groq 70b
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "system", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                        "max_tokens": 600,
                    }
                )
                r.raise_for_status()
                usage = r.json().get("usage", {})
                await redis_incr("groq_tokens_today", usage.get("total_tokens", 0))
                content = r.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
                model_used = "llama-3.3-70b-versatile"

        # Save to daily_synthesis
        await pg_execute("""
            INSERT INTO daily_synthesis
                (user_id, synthesis_date, end_of_day_synthesis, key_insight,
                 recommended_framing, model_used)
            VALUES ('shivam', CURRENT_DATE, $1, $2, $3, $4)
            ON CONFLICT (user_id, synthesis_date) DO UPDATE
            SET end_of_day_synthesis = $1,
                key_insight = $2,
                recommended_framing = $3,
                model_used = $4
        """, result.get("end_of_day_synthesis", ""),
            result.get("key_insight", ""),
            result.get("recommended_framing", ""),
            model_used)

        log.info(f"Nightly synthesis saved ({model_used})")

    except Exception as e:
        log.error(f"Nightly synthesis failed: {e}")


async def run_morning_briefing():
    """
    Morning briefing at 08:00 IST.
    Compiles nightly synthesis + queued observations + task recommendations.
    """
    log.info("Running morning briefing")

    try:
        # Get last night's synthesis
        synthesis = await pg_fetchrow("""
            SELECT end_of_day_synthesis, key_insight, recommended_framing
            FROM daily_synthesis
            WHERE synthesis_date = CURRENT_DATE - 1
            ORDER BY created_at DESC LIMIT 1
        """)

        # Get queued observations
        queued = await pg_fetch("""
            SELECT observation_text, confidence
            FROM morning_briefing_queue
            WHERE delivered = FALSE
            ORDER BY confidence DESC LIMIT 3
        """)

        # Get top tasks
        tasks = await pg_fetch("""
            SELECT title, faction, tws, deferral_count
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
            ORDER BY tws DESC NULLS LAST
            LIMIT 5
        """)

        # Get recent pattern
        pattern = await pg_fetchrow("""
            SELECT description FROM detected_patterns
            WHERE status = 'active' AND confidence > 0.6
            ORDER BY last_confirmed_at DESC LIMIT 1
        """)

        # Build context for morning brief LLM call
        context_data = {
            "synthesis": dict(synthesis) if synthesis else None,
            "queued_observations": [dict(q) for q in queued],
            "top_tasks": [dict(t) for t in tasks],
            "behavioral_observation": pattern["description"] if pattern else None,
            "current_time": datetime.now().isoformat(),
        }

        if not GROQ_API_KEY:
            return

        if not await _check_token_budget():
            return

        context_str = json.dumps(context_data, default=str)
        prompt = MORNING_BRIEF_PROMPT.format(context=context_str)

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "system", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 350,
                }
            )
            r.raise_for_status()

            usage = r.json().get("usage", {})
            await redis_incr("groq_tokens_today", usage.get("total_tokens", 0))

            brief = r.json()["choices"][0]["message"]["content"]

        # Send briefing
        await _send_telegram(f"☀️ *Morning Briefing*\n\n{brief}")

        # Mark queued observations as delivered
        if queued:
            await pg_execute("""
                UPDATE morning_briefing_queue
                SET delivered = TRUE
                WHERE delivered = FALSE
            """)

        log.info("Morning briefing sent")

    except Exception as e:
        log.error(f"Morning briefing failed: {e}")


async def decay_neo4j_weights():
    """
    Weekly Sunday decay: all Neo4j edge weights × 0.95.
    This implements Hebbian forgetting — pathways not reinforced decay.
    """
    log.info("Decaying Neo4j edge weights by 0.95")

    try:
        from services.neo4j_service import get_driver
        driver = await get_driver()

        async with driver.session() as s:
            result = await s.run("""
                MATCH ()-[r]->()
                WHERE r.weight IS NOT NULL
                SET r.weight = r.weight * 0.95
                RETURN count(r) AS updated
            """)
            record = await result.single()
            count = record["updated"] if record else 0
            log.info(f"Decayed {count} edge weights by 0.95")

    except Exception as e:
        log.error(f"Neo4j weight decay failed: {e}")


async def reset_daily_token_counter():
    """Reset the daily Groq token counter. Run at midnight IST."""
    from core.db import get_redis
    r = await get_redis()
    await r.set("groq_tokens_today", 0)
    log.info("Daily Groq token counter reset")
