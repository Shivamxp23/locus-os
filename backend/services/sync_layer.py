# /opt/locus/backend/services/sync_layer.py
# Tri-store sync: Neo4j ↔ Postgres ↔ Qdrant
#
# Every write operation should go through this layer to ensure
# all three stores represent the same reality.
#
# Write path (every Engine 1 write must do ALL of these):
#   1. Write to Postgres (source of truth for structured data)
#   2. Write to Neo4j (graph relationships)
#   3. Write to Qdrant (semantic search vectors)
#   4. Emit behavioral_event for audit trail
#
# Read path:
#   Use context.py brain_dump (already reads all three in parallel)

import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import httpx

log = logging.getLogger("locus-sync")

DATABASE_URL = os.getenv("DATABASE_URL", "")
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


# ── Postgres helpers ─────────────────────────────────────────────────────────

async def _pg_connect():
    """Get a Postgres connection."""
    return await asyncpg.connect(DATABASE_URL)


async def record_behavioral_event(
    event_type: str,
    data: dict,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> bool:
    """Write an audit event to behavioral_events. Every sync op logs here."""
    if not DATABASE_URL:
        return False
    try:
        conn = await _pg_connect()
        try:
            await conn.execute(
                """INSERT INTO behavioral_events (user_id, event_type, entity_type, data)
                   VALUES ('shivam', $1, $2, $3)""",
                event_type,
                entity_type,
                json.dumps(data)[:1000],
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        log.warning(f"behavioral_event write failed: {e}")
        return False


# ── Neo4j helpers ────────────────────────────────────────────────────────────

async def _neo4j_driver():
    from neo4j import AsyncGraphDatabase
    return AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))


# ── Sync Operations ─────────────────────────────────────────────────────────

async def sync_vault_note(
    file_path: str,
    vault_section: str,
    tags: list[str],
    classification: Optional[str] = None,
    entities: Optional[list[str]] = None,
    concepts: Optional[list[str]] = None,
    summary: Optional[str] = None,
    faction: Optional[str] = None,
) -> dict:
    """
    Sync a vault note's metadata across all three stores.

    This is called AFTER the note's propositions have been chunked and
    embedded into Qdrant (that part is handled by vault_indexer_v2).

    What this function does:
      1. Write vault_note metadata to Postgres behavioral_events
      2. Write entities/concepts to Neo4j as graph nodes
      3. Return sync status
    """
    results = {"postgres": False, "neo4j": False}

    # ── Postgres: behavioral event ──
    try:
        results["postgres"] = await record_behavioral_event(
            event_type="vault_index",
            data={
                "file": file_path,
                "section": vault_section,
                "classification": classification,
                "faction": faction,
                "tags": tags[:10],
                "entity_count": len(entities or []),
                "concept_count": len(concepts or []),
            },
            entity_type="vault_note",
        )
    except Exception as e:
        log.warning(f"Sync vault→postgres failed: {e}")

    # ── Neo4j: graph relationships ──
    if entities or concepts or tags:
        try:
            driver = await _neo4j_driver()
            async with driver.session() as s:
                # Ensure Person node exists
                await s.run("MERGE (p:Person {name: 'Shivam'})")

                # Link entities as interests
                for entity in (entities or [])[:10]:
                    entity = entity.strip().lower()
                    if len(entity) > 2:
                        await s.run(
                            """MERGE (i:Interest {name: $name})
                               SET i.last_mentioned = datetime()
                               WITH i
                               MATCH (p:Person {name: 'Shivam'})
                               MERGE (p)-[:INTERESTED_IN]->(i)""",
                            name=entity,
                        )

                # Link concepts as interests too (they're semantically similar)
                for concept in (concepts or [])[:8]:
                    concept = concept.strip().lower()
                    if len(concept) > 2:
                        await s.run(
                            """MERGE (i:Interest {name: $name})
                               SET i.last_mentioned = datetime()
                               WITH i
                               MATCH (p:Person {name: 'Shivam'})
                               MERGE (p)-[:INTERESTED_IN]->(i)""",
                            name=concept,
                        )

            await driver.close()
            results["neo4j"] = True
        except Exception as e:
            log.warning(f"Sync vault→neo4j failed: {e}")

    return results


async def sync_task_create(
    title: str,
    faction: str,
    priority: int,
    urgency: int,
    difficulty: int,
    description: Optional[str] = None,
    estimated_hours: float = 1.0,
    source: str = "api",
) -> dict:
    """
    Sync a new task creation across all stores.

    1. Postgres: INSERT into tasks (done by caller)
    2. Neo4j: Create Task node linked to Person
    3. Qdrant: Embed task title+description for semantic retrieval
    4. Behavioral event
    """
    results = {"neo4j": False, "qdrant": False, "event": False}

    # ── Neo4j: task node ──
    try:
        driver = await _neo4j_driver()
        async with driver.session() as s:
            await s.run("MERGE (p:Person {name: 'Shivam'})")
            await s.run(
                """MERGE (t:Task {title: $title})
                   ON CREATE SET t.faction = $faction,
                                 t.priority = $priority,
                                 t.difficulty = $difficulty,
                                 t.created_at = datetime(),
                                 t.status = 'pending'
                   SET t.last_updated = datetime()
                   WITH t
                   MATCH (p:Person {name: 'Shivam'})
                   MERGE (p)-[:HAS_TASK]->(t)""",
                title=title,
                faction=faction,
                priority=priority,
                difficulty=difficulty,
            )
        await driver.close()
        results["neo4j"] = True
    except Exception as e:
        log.warning(f"Sync task→neo4j failed: {e}")

    # ── Qdrant: embed for semantic search ──
    try:
        from services.qdrant_service import upsert_document
        embed_text = f"Task: {title}. {description or ''}"
        ok = await upsert_document(
            source_id=f"task::{title}",
            text=embed_text,
            metadata={
                "type": "task",
                "title": title,
                "faction": faction,
                "priority": priority,
                "source": source,
            },
        )
        results["qdrant"] = ok
    except Exception as e:
        log.warning(f"Sync task→qdrant failed: {e}")

    # ── Behavioral event ──
    results["event"] = await record_behavioral_event(
        event_type="task_create",
        data={"title": title, "faction": faction, "source": source},
        entity_type="task",
    )

    return results


async def sync_capture(
    text: str,
    source: str = "telegram",
) -> dict:
    """
    Sync a new capture (quick note) across stores.

    1. Postgres: INSERT into captures (done by caller)
    2. Qdrant: Embed for retrieval
    3. Neo4j: Extract topics and link
    4. Behavioral event
    """
    results = {"qdrant": False, "neo4j": False, "event": False}

    # ── Qdrant ──
    try:
        from services.qdrant_service import upsert_document
        ok = await upsert_document(
            source_id=f"capture::{text[:50]}::{datetime.now(timezone.utc).isoformat()}",
            text=text,
            metadata={
                "type": "capture",
                "source": source,
                "text": text[:500],
                "captured_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        results["qdrant"] = ok
    except Exception as e:
        log.warning(f"Sync capture→qdrant failed: {e}")

    # ── Behavioral event ──
    results["event"] = await record_behavioral_event(
        event_type="capture",
        data={"text": text[:200], "source": source},
        entity_type="capture",
    )

    return results


async def sync_checkin(
    checkin_type: str,
    dcs: Optional[float] = None,
    mode: Optional[str] = None,
    data: Optional[dict] = None,
) -> dict:
    """
    Sync a check-in event to Neo4j behavioral patterns.

    1. Postgres: INSERT into daily_logs (done by caller)
    2. Neo4j: Update behavioral patterns
    3. Behavioral event
    """
    results = {"neo4j": False, "event": False}

    # ── Neo4j: behavioral state ──
    if dcs is not None:
        try:
            driver = await _neo4j_driver()
            async with driver.session() as s:
                await s.run(
                    """MATCH (p:Person {name: 'Shivam'})
                       SET p.last_dcs = $dcs,
                           p.last_mode = $mode,
                           p.last_checkin = datetime()""",
                    dcs=dcs,
                    mode=mode or "UNKNOWN",
                )
            await driver.close()
            results["neo4j"] = True
        except Exception as e:
            log.warning(f"Sync checkin→neo4j failed: {e}")

    # ── Behavioral event ──
    results["event"] = await record_behavioral_event(
        event_type=f"checkin_{checkin_type}",
        data={
            "checkin_type": checkin_type,
            "dcs": dcs,
            "mode": mode,
            **(data or {}),
        },
        entity_type="checkin",
    )

    return results


async def sync_learn(
    extracted: dict,
    user_message: str,
    bot_reply: str,
) -> dict:
    """
    Sync learned insights from conversation.
    This wraps the existing learn logic and adds Qdrant indexing.

    1. Postgres: ai_interactions (done by caller in context.py)
    2. Neo4j: interests, projects, avoidances, patterns, traits (done by context.py)
    3. Qdrant: embed the conversation for retrieval
    """
    results = {"qdrant": False}

    # ── Qdrant: embed conversation for future retrieval ──
    try:
        from services.qdrant_service import upsert_document
        convo_text = f"User: {user_message}\nLocus: {bot_reply}"
        topics = extracted.get("topics", [])
        insight = extracted.get("insight", "")
        embed_text = f"{convo_text}\nTopics: {', '.join(topics)}\nInsight: {insight}"

        ok = await upsert_document(
            source_id=f"convo::{datetime.now(timezone.utc).isoformat()}::{user_message[:30]}",
            text=embed_text[:4000],
            metadata={
                "type": "conversation",
                "topics": topics[:5],
                "insight": insight[:200] if insight else None,
                "emotional_state": extracted.get("emotional_state"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        results["qdrant"] = ok
    except Exception as e:
        log.warning(f"Sync learn→qdrant failed: {e}")

    return results


# ── Health check ─────────────────────────────────────────────────────────────

async def sync_health() -> dict:
    """Check connectivity to all three stores."""
    results = {}

    # Postgres
    try:
        conn = await _pg_connect()
        await conn.fetchval("SELECT 1")
        await conn.close()
        results["postgres"] = "ok"
    except Exception as e:
        results["postgres"] = f"fail: {e}"

    # Neo4j
    try:
        driver = await _neo4j_driver()
        async with driver.session() as s:
            r = await s.run("RETURN 1 AS n")
            await r.single()
        await driver.close()
        results["neo4j"] = "ok"
    except Exception as e:
        results["neo4j"] = f"fail: {e}"

    # Qdrant
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{os.getenv('QDRANT_URL', 'http://qdrant:6333')}/collections")
            results["qdrant"] = "ok" if r.status_code == 200 else f"http {r.status_code}"
    except Exception as e:
        results["qdrant"] = f"fail: {e}"

    return results
