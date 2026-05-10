import os
import json
import logging
import httpx
from datetime import datetime

log = logging.getLogger("locus-inner-loop")

API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")
API_HEADERS = {"X-Service-Token": SERVICE_TOKEN}
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

INNER_LOOP_PROMPT = """You are Locus's internal reasoning process. You are NOT talking to Shivam. You are thinking about Shivam.

Your job: generate 0-2 specific, evidence-based observations about what you are noticing in his data right now.

Rules:
- Be specific. Cite data points. Not generic advice.
- If you have nothing meaningful, return empty array.
- Never fabricate. If the data doesn't support it, don't say it.
- You know Shivam: direct, no sycophancy, push-back welcome, technically sharp, filmmaker + developer.

Return JSON:
{
  "observations": [
    {
      "text": "string",
      "confidence": 0.0,
      "should_surface": true|false,
      "surface_timing": "now|morning_brief|hold"
    }
  ]
}
"""

DEEP_SYNTHESIS_PROMPT = """You are Locus's nightly deep synthesis process.
Analyze today's events, patterns, and states.

Generate:
1. End of day synthesis: what kind of day was it really?
2. One key insight Shivam might not have noticed
3. Recommended framing for tomorrow based on today's trajectory

Return JSON:
{
  "end_of_day_synthesis": "string",
  "key_insight": "string",
  "recommended_framing": "string"
}
"""

async def run_standard_pass():
    """Runs every 90 minutes."""
    log.info("Running standard 90-min inner loop pass.")

    events = []
    state = {}
    try:
        async with httpx.AsyncClient() as client:
            r1 = await client.get(f"{API_URL}/api/v1/context/postgres", params={"scope": "last_6h"}, headers=API_HEADERS)
            if r1.status_code == 200:
                events = r1.json().get("events", [])
            r2 = await client.get(f"{API_URL}/api/v1/context/state", headers=API_HEADERS)
            if r2.status_code == 200:
                state = r2.json()
    except Exception:
        pass

    context_data = {"recent_events": events, "current_state": state}

    if not GROQ_API_KEY:
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": INNER_LOOP_PROMPT},
                        {"role": "user", "content": f"Current Data:\n{json.dumps(context_data)}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4
                }
            )
            if r.status_code == 200:
                result = json.loads(r.json()["choices"][0]["message"]["content"])
                observations = result.get("observations", [])

                for obs in observations:
                    if obs.get("should_surface"):
                        if obs.get("surface_timing") == "now" and obs.get("confidence", 0) > 0.65:
                            msg = f"💡 *Observation:*\n{obs['text']}"
                            log.info(f"Surfacing proactive observation: {obs['text']}")
                            try:
                                token = os.getenv("TELEGRAM_TOKEN")
                                chat_id = os.getenv("TELEGRAM_OWNER_ID")
                                if token and chat_id:
                                    await client.post(
                                        f"https://api.telegram.org/bot{token}/sendMessage",
                                        json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
                                    )
                            except Exception as e:
                                log.error(f"Failed to send proactive Telegram message: {e}")
                        elif obs.get("surface_timing") == "morning_brief":
                            try:
                                await client.post(
                                    f"{API_URL}/api/v1/context/state",
                                    json={"morning_briefing_queue": obs['text']},
                                    headers=API_HEADERS
                                )
                            except Exception:
                                pass
    except Exception as e:
        log.error(f"Inner loop pass failed: {e}")

async def run_nightly_synthesis():
    """Runs at 03:00 IST."""
    log.info("Running nightly deep synthesis.")

    events = []
    try:
        async with httpx.AsyncClient() as client:
            r1 = await client.get(f"{API_URL}/api/v1/context/postgres", params={"scope": "last_24h"}, headers=API_HEADERS)
            if r1.status_code == 200:
                events = r1.json().get("events", [])
    except Exception:
        pass

    context_data = {"daily_events": events}

    if not GROQ_API_KEY:
        return

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": DEEP_SYNTHESIS_PROMPT},
                        {"role": "user", "content": f"Today's Data:\n{json.dumps(context_data)}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.3
                }
            )
            if r.status_code == 200:
                result = json.loads(r.json()["choices"][0]["message"]["content"])
                await client.post(
                    f"{API_URL}/api/v1/context/synthesis/daily",
                    json=result,
                    headers=API_HEADERS
                )
    except Exception as e:
        log.error(f"Nightly synthesis failed: {e}")

async def run_morning_briefing():
    """Runs at 08:00 IST."""
    log.info("Running morning briefing.")

    try:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_OWNER_ID")
        if not token or not chat_id: return

        brief_data = {}
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_URL}/api/v1/context/state", headers=API_HEADERS)
            if r.status_code == 200:
                brief_data = r.json()

        msg = "☀️ *Morning Briefing*\n\n"
        if brief_data.get("morning_briefing_queue"):
            msg += f"💡 {brief_data['morning_briefing_queue']}\n\n"
        msg += "Your day awaits."

        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}
            )
    except Exception as e:
        log.error(f"Morning briefing failed: {e}")

async def decay_neo4j_weights():
    """Runs weekly on Sunday to decay all edge weights by 0.95."""
    log.info("Decaying Neo4j edge weights by 0.95.")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{API_URL}/api/v1/brain/pathways/decay",
                headers=API_HEADERS
            )
    except Exception as e:
        log.error(f"Neo4j weight decay failed: {e}")
