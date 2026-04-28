# /opt/locus/backend/services/vault_jobs.py
# Real implementations — nightly/weekly brain jobs

import os
import logging
import json
import asyncpg
import httpx
from datetime import datetime, date
from pathlib import Path

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "")
VAULT_PATH = "/vault"


async def _send_telegram(message: str):
    """Send a Telegram DM to the owner."""
    if not TELEGRAM_TOKEN or not TELEGRAM_OWNER_ID:
        log.warning("Telegram credentials not set — cannot send alert")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_OWNER_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                }
            )
    except Exception as e:
        log.warning(f"Telegram alert send failed: {e}")


async def nightly_diff():
    """
    Process new/changed vault files since last run.
    1. Run proposition-based indexing (vault_indexer_v2)
    2. Run enrichment on un-enriched files (vault_enricher)
    Runs at 11:30 PM via APScheduler.
    """
    log.info("=== Nightly Diff: starting ===")

    # Phase 1: Proposition-based indexing into Qdrant
    try:
        from services.vault_indexer_v2 import run_incremental_index
        summary = await run_incremental_index()
        log.info(
            f"Nightly indexer: {summary.get('indexed', 0)} files indexed, "
            f"Qdrant {summary.get('qdrant_before', 0)}→{summary.get('qdrant_after', 0)} points"
        )
    except Exception as e:
        log.error(f"Nightly indexer v2 failed: {e}")

    # Phase 2: Enrichment (annotation with ⟨locus⟩ section)
    try:
        from services.vault_enricher import run_enrichment
        enriched = await run_enrichment()
        log.info(f"Nightly enricher: {enriched} files enriched")
    except Exception as e:
        log.error(f"Nightly enricher failed: {e}")


async def weekly_synthesis():
    """
    Full vault + behavioral analysis with Gemini 2.5 Pro.
    Runs Sunday at 2 AM via APScheduler.
    Generates a weekly personality snapshot and insight report.
    """
    log.info("=== Weekly Synthesis: starting ===")
    try:
        if not DATABASE_URL:
            log.warning("DATABASE_URL not set, skipping weekly synthesis")
            return

        conn = await asyncpg.connect(DATABASE_URL)

        try:
            # 1. Collect this week's data
            week_data = {}

            # DCS scores
            rows = await conn.fetch("""
                SELECT date, dcs, mode, energy, mood, sleep_quality, stress
                FROM daily_logs
                WHERE checkin_type = 'morning'
                  AND date >= NOW() - INTERVAL '7 days'
                ORDER BY date
            """)
            week_data["dcs_entries"] = [
                f"{r['date']}: DCS={r['dcs']} mode={r['mode']} E={r['energy']} M={r['mood']} S={r['sleep_quality']} St={r['stress']}"
                for r in rows if r['dcs']
            ]

            # Tasks completed
            rows = await conn.fetch("""
                SELECT title, faction, actual_hours, quality
                FROM tasks
                WHERE status = 'done'
                  AND completed_at >= NOW() - INTERVAL '7 days'
                ORDER BY completed_at
            """)
            week_data["completed"] = [
                f"{r['title']} ({r['faction']}, {r['actual_hours']}h, quality:{r['quality']})"
                for r in rows
            ]

            # Tasks deferred
            rows = await conn.fetch("""
                SELECT title, faction, deferral_count
                FROM tasks
                WHERE status = 'deferred'
                  AND created_at >= NOW() - INTERVAL '7 days'
            """)
            week_data["deferred"] = [
                f"{r['title']} ({r['faction']}, deferred {r['deferral_count']}x)"
                for r in rows
            ]

            # Avoidances
            rows = await conn.fetch("""
                SELECT avoided, avoided_reason
                FROM daily_logs
                WHERE checkin_type = 'evening'
                  AND avoided IS NOT NULL
                  AND date >= NOW() - INTERVAL '7 days'
            """)
            week_data["avoidances"] = [
                f"{r['avoided']}: {r['avoided_reason'] or 'no reason given'}"
                for r in rows
            ]

            # Build synthesis prompt
            prompt = f"""Analyze this week's behavioral data for Shivam:

DCS Scores: {json.dumps(week_data.get('dcs_entries', []))}
Tasks Completed: {json.dumps(week_data.get('completed', []))}
Tasks Deferred: {json.dumps(week_data.get('deferred', []))}
Avoidances: {json.dumps(week_data.get('avoidances', []))}

Produce a JSON report with:
{{
  "energy_pattern": "description of energy trend this week",
  "productivity_summary": "what got done vs. what was avoided",
  "faction_balance": "which factions were neglected vs over-served",
  "behavioral_insights": ["3-5 factual observations about patterns"],
  "recommendations": ["3 specific actionable suggestions for next week"],
  "risk_flags": ["any concerning patterns: burnout, avoidance spirals, faction collapse"]
}}

Return ONLY JSON."""

            # Call Gemini for deep analysis
            from services.llm import call_llm
            response = await call_llm(prompt, task_type="weekly")

            try:
                report = json.loads(response)
            except json.JSONDecodeError:
                report = {"raw": response[:2000]}

            # Write personality snapshot
            today = date.today()
            await conn.execute("""
                INSERT INTO personality_snapshots (user_id, snapshot_date, snapshot_data)
                VALUES ('shivam', $1, $2)
                ON CONFLICT (user_id, snapshot_date) DO UPDATE SET
                    snapshot_data = EXCLUDED.snapshot_data
            """, today, json.dumps(report))

            log.info(f"Weekly synthesis complete. Snapshot saved for {today}.")

        finally:
            await conn.close()

    except Exception as e:
        log.error(f"Weekly synthesis failed: {e}")


async def nightly_pattern_detection():
    """
    Feed 7-day behavioral log to LLM and extract factual observations.
    Writes detected patterns to Neo4j.
    Runs at 2:30 AM daily.
    """
    log.info("=== Pattern Detection: starting ===")
    try:
        if not DATABASE_URL:
            return

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # Get recent behavioral events
            rows = await conn.fetch("""
                SELECT event_type, data, created_at
                FROM behavioral_events
                WHERE user_id = 'shivam'
                  AND created_at >= NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 50
            """)

            if len(rows) < 5:
                log.info("Not enough behavioral data for pattern detection (need 5+)")
                return

            events_text = "\n".join([
                f"{r['created_at'].strftime('%a %H:%M')} [{r['event_type']}] {r['data'][:200]}"
                for r in rows
            ])

            from services.llm import call_llm
            prompt = f"""Analyze these behavioral events and extract 3-5 factual observations.
Focus on: timing patterns, faction preferences, avoidance triggers, energy correlations.

Events:
{events_text}

Return JSON:
{{"observations": ["observation 1", "observation 2", ...]}}
Return ONLY JSON."""

            response = await call_llm(prompt, task_type="nightly")
            try:
                data = json.loads(response)
                observations = data.get("observations", [])
            except:
                return

            # Write observations to Neo4j as Pattern nodes
            neo4j_url = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
            neo4j_pw = os.getenv("NEO4J_PASSWORD", "")

            try:
                from neo4j import AsyncGraphDatabase
                driver = AsyncGraphDatabase.driver(neo4j_url, auth=("neo4j", neo4j_pw))
                async with driver.session() as s:
                    for obs in observations[:5]:
                        await s.run("""
                            MERGE (pat:Pattern {description: $desc})
                            ON CREATE SET pat.strength = 1.0,
                                          pat.first_observed = datetime(),
                                          pat.type = 'automated'
                            ON MATCH SET pat.strength = pat.strength + 0.1,
                                         pat.last_reinforced = datetime()
                            WITH pat
                            MATCH (p:Person {name: 'Shivam'})
                            MERGE (p)-[:EXHIBITS_PATTERN]->(pat)
                        """, desc=obs)
                await driver.close()
                log.info(f"Pattern detection: wrote {len(observations)} observations to Neo4j")
            except Exception as e:
                log.warning(f"Neo4j pattern write failed: {e}")

        finally:
            await conn.close()

    except Exception as e:
        log.error(f"Pattern detection failed: {e}")


async def exhaustion_check():
    """
    Check for 3+ consecutive days of DCS < 4 → send Telegram alert.
    Runs at 3 AM daily.
    """
    log.info("=== Exhaustion Check ===")
    try:
        if not DATABASE_URL:
            return

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("""
                SELECT date, dcs FROM daily_logs
                WHERE user_id = 'shivam' AND checkin_type = 'morning'
                  AND dcs IS NOT NULL
                ORDER BY date DESC LIMIT 5
            """)

            low_days = sum(1 for r in rows if r['dcs'] and float(r['dcs']) < 4.0)
            if low_days >= 3:
                dcs_vals = [f"{r['date'].strftime('%a')}: {r['dcs']}" for r in rows[:low_days]]
                log.warning(f"EXHAUSTION ALERT: {low_days} consecutive low-DCS days!")

                await conn.execute("""
                    INSERT INTO behavioral_events (user_id, event_type, data)
                    VALUES ('shivam', 'exhaustion_alert', $1)
                """, json.dumps({"low_days": low_days, "dcs_values": [float(r['dcs']) for r in rows[:low_days]]}))

                # Actually alert you
                msg = (
                    f"🔴 *EXHAUSTION ALERT*\n\n"
                    f"{low_days} consecutive days of DCS < 4:\n"
                    + "\n".join(f"  • {v}" for v in dcs_vals)
                    + "\n\nProtect non-negotiables. No productive expectations today."
                )
                await _send_telegram(msg)
        finally:
            await conn.close()

    except Exception as e:
        log.error(f"Exhaustion check failed: {e}")


async def dead_node_detection():
    """
    Flag projects with 0 activity in 60 days → Telegram alert.
    Runs Sunday at 6 AM.
    """
    log.info("=== Dead Node Detection ===")
    try:
        if not DATABASE_URL:
            return

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("""
                SELECT id, title, faction, status, last_activity_at
                FROM projects
                WHERE user_id = 'shivam'
                  AND status = 'active'
                  AND last_activity_at < NOW() - INTERVAL '60 days'
            """)

            for r in rows:
                log.warning(f"DEAD NODE: Project '{r['title']}' ({r['faction']}) — "
                           f"no activity since {r['last_activity_at']}")
                await conn.execute("""
                    INSERT INTO behavioral_events (user_id, event_type, data)
                    VALUES ('shivam', 'dead_node', $1)
                """, json.dumps({"project": r['title'], "faction": r['faction'],
                                "last_activity": str(r['last_activity_at'])}))

            if rows:
                log.info(f"Dead node detection: found {len(rows)} stale projects")
                faction_emoji = {"health": "🟢", "leverage": "🔵", "craft": "🟠", "expression": "🟣"}
                lines = [f"🕸️ *Dead Node Alert* — {len(rows)} stale project(s):\n"]
                for r in rows:
                    e = faction_emoji.get(r['faction'], '⚪')
                    since = r['last_activity_at'].strftime('%b %d') if r['last_activity_at'] else 'unknown'
                    lines.append(f"  {e} *{r['title']}* — no activity since {since}")
                lines.append("\nDecide: pause, abandon, or re-engage this week.")
                await _send_telegram("\n".join(lines))
            else:
                log.info("Dead node detection: all projects active")

        finally:
            await conn.close()

    except Exception as e:
        log.error(f"Dead node detection failed: {e}")
