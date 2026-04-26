"""
context.py — Brain context layer.

  GET  /context/personality     → Neo4j (traits, patterns, interests, projects, avoidances)
  GET  /context/recent_behavior → PostgreSQL (DCS scores, avoidances, mood trend)
  GET  /context/brain_dump      → COMBINED: Neo4j + Postgres + Qdrant stats + pending tasks
  POST /context/learn           → write extracted insights back to Neo4j + behavioral_events
"""

import os
import logging
import asyncio
from fastapi import APIRouter, Header, HTTPException
from datetime import datetime

router = APIRouter()
log = logging.getLogger(__name__)

NEO4J_URL      = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
DATABASE_URL   = os.getenv("DATABASE_URL", "")
SERVICE_TOKEN  = os.getenv("LOCUS_SERVICE_TOKEN", "")


def _check(token):
    if token != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


# ──────────────────────────────────────────────
#  PERSONALITY CONTEXT  (Neo4j)
# ──────────────────────────────────────────────

@router.get("/context/personality")
async def get_personality(x_service_token: str = Header(None)):
    _check(x_service_token)
    return await _fetch_neo4j_personality()


async def _fetch_neo4j_personality() -> dict:
    result = {
        "traits": [],
        "patterns": [],
        "interests": [],
        "active_projects": [],
        "avoidances": [],
    }
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))

        async with driver.session() as s:

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[rel:HAS_TRAIT]->(t:Trait) "
                "RETURN t.name AS name ORDER BY coalesce(rel.confidence, 1.0) DESC LIMIT 10"
            )
            result["traits"] = [rec["name"] async for rec in r]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:EXHIBITS_PATTERN]->(pat:Pattern) "
                "RETURN pat.description AS desc ORDER BY coalesce(pat.strength, 1.0) DESC LIMIT 8"
            )
            result["patterns"] = [rec["desc"] async for rec in r]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:INTERESTED_IN]->(i:Interest) "
                "RETURN i.name AS name ORDER BY coalesce(i.last_mentioned, datetime()) DESC LIMIT 15"
            )
            result["interests"] = [rec["name"] async for rec in r]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:WORKING_ON]->(pr:Project {status:'active'}) "
                "RETURN pr.name AS name"
            )
            result["active_projects"] = [rec["name"] async for rec in r]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:AVOIDS]->(a:Avoidance) "
                "RETURN a.description AS desc ORDER BY coalesce(a.frequency, 1) DESC LIMIT 5"
            )
            result["avoidances"] = [rec["desc"] async for rec in r]

        await driver.close()

    except Exception as e:
        log.warning(f"Neo4j read failed: {e}")

    return result


# ──────────────────────────────────────────────
#  RECENT BEHAVIOUR  (PostgreSQL)
# ──────────────────────────────────────────────

@router.get("/context/recent_behavior")
async def get_recent_behavior(x_service_token: str = Header(None)):
    _check(x_service_token)
    return await _fetch_postgres_behavior()


async def _fetch_postgres_behavior() -> dict:
    result = {
        "recent_dcs": [],
        "last_evening_checkin": None,
        "avoided_recently": [],
        "mood_trend": None,
    }
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)

        rows = await conn.fetch("""
            SELECT date, dcs, mode
            FROM daily_logs
            WHERE checkin_type = 'morning'
              AND date >= NOW() - INTERVAL '7 days'
            ORDER BY date DESC
            LIMIT 7
        """)
        result["recent_dcs"] = [
            f"{row['date'].strftime('%a')}: DCS={row['dcs']} ({row['mode']})"
            for row in rows if row["dcs"]
        ]

        row = await conn.fetchrow("""
            SELECT did_today, avoided, avoided_reason, tomorrow_priority
            FROM daily_logs
            WHERE checkin_type = 'evening'
              AND did_today IS NOT NULL
            ORDER BY date DESC
            LIMIT 1
        """)
        if row:
            parts = [f"Did: {row['did_today']}"]
            if row['avoided']:
                parts.append(f"Avoided: {row['avoided']}")
                if row['avoided_reason']:
                    parts.append(f"Reason: {row['avoided_reason']}")
            if row['tomorrow_priority']:
                parts.append(f"Tomorrow: {row['tomorrow_priority']}")
            result["last_evening_checkin"] = ". ".join(parts)

        rows = await conn.fetch("""
            SELECT avoided, COUNT(*) AS cnt
            FROM daily_logs
            WHERE checkin_type = 'evening'
              AND avoided IS NOT NULL
              AND date >= NOW() - INTERVAL '14 days'
            GROUP BY avoided
            ORDER BY cnt DESC
            LIMIT 3
        """)
        result["avoided_recently"] = [row["avoided"] for row in rows]

        rows = await conn.fetch("""
            SELECT
                AVG(CASE WHEN date >= NOW() - INTERVAL '7 days' THEN mood END) AS recent_avg,
                AVG(CASE WHEN date < NOW() - INTERVAL '7 days'
                          AND date >= NOW() - INTERVAL '14 days' THEN mood END) AS prev_avg
            FROM daily_logs
            WHERE checkin_type = 'morning' AND mood IS NOT NULL
        """)
        if rows and rows[0]["recent_avg"] and rows[0]["prev_avg"]:
            diff = float(rows[0]["recent_avg"]) - float(rows[0]["prev_avg"])
            if diff > 0.5:
                result["mood_trend"] = "improving"
            elif diff < -0.5:
                result["mood_trend"] = "declining"
            else:
                result["mood_trend"] = "stable"

        await conn.close()

    except Exception as e:
        log.warning(f"PostgreSQL behavioral read failed: {e}")

    return result


# ──────────────────────────────────────────────
#  BRAIN DUMP  (All sources combined)
# ──────────────────────────────────────────────

@router.get("/context/brain_dump")
async def brain_dump(x_service_token: str = Header(None)):
    """
    Single endpoint that pulls ALL context in parallel:
    - Neo4j personality graph
    - PostgreSQL behavioral patterns + today's state
    - Qdrant collection stats
    - Top pending tasks from Postgres
    """
    _check(x_service_token)

    # Parallel fetch
    neo4j_task    = asyncio.create_task(_fetch_neo4j_personality())
    behavior_task = asyncio.create_task(_fetch_postgres_behavior())
    qdrant_task   = asyncio.create_task(_fetch_qdrant_stats())
    tasks_task    = asyncio.create_task(_fetch_pending_tasks())
    today_task    = asyncio.create_task(_fetch_today_status())

    personality, behavior, qdrant_stats, pending_tasks, today = await asyncio.gather(
        neo4j_task, behavior_task, qdrant_task, tasks_task, today_task,
        return_exceptions=True
    )

    # Handle exceptions gracefully
    if isinstance(personality, Exception):
        log.warning(f"brain_dump neo4j failed: {personality}")
        personality = {"traits": [], "patterns": [], "interests": [], "active_projects": [], "avoidances": []}
    if isinstance(behavior, Exception):
        log.warning(f"brain_dump postgres failed: {behavior}")
        behavior = {"recent_dcs": [], "last_evening_checkin": None, "avoided_recently": [], "mood_trend": None}
    if isinstance(qdrant_stats, Exception):
        qdrant_stats = {"points_count": 0, "status": "error"}
    if isinstance(pending_tasks, Exception):
        pending_tasks = []
    if isinstance(today, Exception):
        today = {"dcs": None, "mode": None, "pending": []}

    return {
        "personality": personality,
        "behavior":    behavior,
        "today":       today,
        "pending_tasks": pending_tasks,
        "qdrant":      qdrant_stats,
        "fetched_at":  datetime.now().isoformat(),
    }


async def _fetch_qdrant_stats() -> dict:
    try:
        from services.qdrant_service import collection_stats
        return await collection_stats()
    except Exception as e:
        return {"points_count": 0, "status": f"error: {e}"}


async def _fetch_pending_tasks() -> list:
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch("""
                SELECT id, title, faction, priority, urgency, difficulty, tws,
                       estimated_hours, deferral_count
                FROM tasks
                WHERE user_id = 'shivam' AND status = 'pending'
                ORDER BY tws DESC
                LIMIT 10
            """)
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as e:
        log.warning(f"Pending tasks fetch failed: {e}")
        return []


async def _fetch_today_status() -> dict:
    try:
        import asyncpg
        from datetime import date
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            today = date.today()
            rows = await conn.fetch("""
                SELECT checkin_type, dcs, mode, energy, mood, sleep_quality, stress,
                       intention, did_today, avoided, tomorrow_priority
                FROM daily_logs
                WHERE user_id = 'shivam' AND date = $1
            """, today)
            done = [r['checkin_type'] for r in rows]
            pending = [t for t in ['morning', 'afternoon', 'evening', 'night'] if t not in done]
            checkins = {r['checkin_type']: dict(r) for r in rows}
            return {
                "date": str(today),
                "checkins": checkins,
                "pending": pending,
                "dcs": checkins.get('morning', {}).get('dcs'),
                "mode": checkins.get('morning', {}).get('mode'),
            }
        finally:
            await conn.close()
    except Exception as e:
        log.warning(f"Today status fetch failed: {e}")
        return {"dcs": None, "mode": None, "pending": []}


# ──────────────────────────────────────────────
#  LEARNING WRITE-BACK  (Neo4j + behavioral_events)
# ──────────────────────────────────────────────

@router.post("/context/learn")
async def learn(data: dict, x_service_token: str = Header(None)):
    _check(x_service_token)

    extracted    = data.get("extracted", {})
    user_message = data.get("user_message", "")
    bot_reply    = data.get("bot_reply", "")

    if not extracted:
        return {"status": "skipped"}

    # ── Write to PostgreSQL ai_interactions ──
    try:
        import asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            INSERT INTO ai_interactions
              (user_id, interface, interaction_type, prompt, response, model_used)
            VALUES ('shivam', 'telegram', 'conversation', $1, $2, 'groq-llama3.3-70b')
        """, user_message, bot_reply)
        await conn.close()
    except Exception as e:
        log.warning(f"ai_interactions write failed: {e}")

    # ── Write to Neo4j ──
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))

        async with driver.session() as s:

            await s.run("MERGE (p:Person {name: 'Shivam'})")

            for topic in extracted.get("topics", []):
                topic = topic.strip().lower()
                if len(topic) > 2:
                    await s.run("""
                        MERGE (i:Interest {name: $topic})
                        SET i.last_mentioned = datetime()
                        WITH i
                        MATCH (p:Person {name: 'Shivam'})
                        MERGE (p)-[:INTERESTED_IN]->(i)
                    """, topic=topic)

            for proj in extracted.get("projects_mentioned", []):
                proj = proj.strip()
                if proj:
                    await s.run("""
                        MERGE (pr:Project {name: $proj})
                        ON CREATE SET pr.status = 'active', pr.first_seen = datetime()
                        SET pr.last_mentioned = datetime()
                        WITH pr
                        MATCH (p:Person {name: 'Shivam'})
                        MERGE (p)-[:WORKING_ON]->(pr)
                    """, proj=proj)

            if extracted.get("avoidance"):
                await s.run("""
                    MERGE (a:Avoidance {description: $desc})
                    ON CREATE SET a.frequency = 1, a.first_seen = datetime()
                    ON MATCH SET a.frequency = a.frequency + 1, a.last_seen = datetime()
                    WITH a
                    MATCH (p:Person {name: 'Shivam'})
                    MERGE (p)-[:AVOIDS]->(a)
                """, desc=extracted["avoidance"])

            if extracted.get("insight"):
                await s.run("""
                    MERGE (pat:Pattern {description: $desc})
                    ON CREATE SET pat.strength = 1.0,
                                  pat.first_observed = datetime(),
                                  pat.type = 'behavioral'
                    ON MATCH SET pat.strength = pat.strength + 0.1,
                                 pat.last_reinforced = datetime()
                    WITH pat
                    MATCH (p:Person {name: 'Shivam'})
                    MERGE (p)-[:EXHIBITS_PATTERN]->(pat)
                """, desc=extracted["insight"])

            if extracted.get("trait"):
                await s.run("""
                    MERGE (t:Trait {name: $name})
                    ON CREATE SET t.confidence = 0.5, t.first_seen = datetime()
                    ON MATCH SET t.confidence = CASE
                        WHEN t.confidence < 1.0 THEN t.confidence + 0.05
                        ELSE 1.0 END,
                        t.last_seen = datetime()
                    WITH t
                    MATCH (p:Person {name: 'Shivam'})
                    MERGE (p)-[rel:HAS_TRAIT]->(t)
                    ON CREATE SET rel.confidence = 0.5
                    ON MATCH SET rel.confidence = CASE
                        WHEN rel.confidence < 1.0 THEN rel.confidence + 0.05
                        ELSE 1.0 END
                """, name=extracted["trait"])

        await driver.close()

    except Exception as e:
        log.warning(f"Neo4j write-back failed: {e}")

    return {"status": "ok"}
