"""
source_retriever.py — System 1.2: Parallel Source Retriever

Based on classifier output, launches PARALLEL async retrievals from all
required sources simultaneously. Uses DIRECT database connections — no
HTTP round-trips through the API.

This is the module that was fundamentally broken before. It was calling
the API's own endpoints via HTTP, which either didn't exist or created
circular dependencies. Now it queries PostgreSQL, Neo4j, Qdrant, Redis,
and the Obsidian vault directly.
"""

import os
import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

import httpx

log = logging.getLogger("locus-source-retriever")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VAULT_DIR = os.getenv("VAULT_DIR", "/vault")

# Temporal scope → PostgreSQL interval mapping
SCOPE_TO_INTERVAL = {
    "last_6h": "6 hours",
    "last_24h": "24 hours",
    "last_7d": "7 days",
    "last_30d": "30 days",
    "all_time": "3650 days",  # ~10 years
}


# ═══════════════════════════════════════════════════════════════
#  POSTGRESQL RETRIEVER — Direct asyncpg queries
# ═══════════════════════════════════════════════════════════════

async def _fetch_postgres(query: str, scope: str, primary_intent: str) -> dict:
    """
    Fetch relevant events from PostgreSQL based on intent and temporal scope.
    Returns structured data for compression via LOCUS_SHORTHAND.
    """
    from core.db import pg_fetch, pg_fetchrow, pg_fetchval

    interval = SCOPE_TO_INTERVAL.get(scope, "7 days")
    result = {
        "events": [],
        "tasks": [],
        "current_dcs": None,
        "faction_scores": None,
        "mood_trend": None,
        "deferred_tasks": [],
    }

    try:
        # ── Always: recent daily logs (mood, energy, sleep) ──
        logs = await pg_fetch("""
            SELECT date, checkin_type, mood, energy, focus, stress,
                   sleep_hours, sleep_quality, dcs, mode,
                   did_today, avoided, avoided_reason, intention
            FROM daily_logs
            WHERE date >= NOW() - $1::interval
            ORDER BY date DESC, created_at DESC
            LIMIT 20
        """, interval)

        for log_row in logs:
            event = {"type": "daily_log", **{k: v for k, v in log_row.items() if v is not None}}
            # Convert date objects to strings for JSON
            if "date" in event:
                event["date"] = str(event["date"])
            result["events"].append(event)

        # ── Current DCS (today's morning check-in) ──
        today_row = await pg_fetchrow("""
            SELECT dcs, mode, mood, energy, stress
            FROM daily_logs
            WHERE date = CURRENT_DATE AND checkin_type = 'morning'
            LIMIT 1
        """)
        if today_row:
            result["current_dcs"] = today_row

        # ── For BEHAVIORAL_PATTERN: deferral patterns ──
        if primary_intent in ("BEHAVIORAL_PATTERN", "INFERENCE_REQUEST", "SYNTHESIS"):
            deferred = await pg_fetch("""
                SELECT t.title, t.deferral_count, t.faction,
                       td.reason, td.deferred_at
                FROM tasks t
                LEFT JOIN task_deferrals td ON t.id = td.task_id
                WHERE t.deferral_count >= 2
                ORDER BY t.deferral_count DESC
                LIMIT 10
            """)
            for d in deferred:
                if d.get("deferred_at"):
                    d["deferred_at"] = str(d["deferred_at"])
            result["deferred_tasks"] = deferred

        # ── For EMOTIONAL_STATE: mood/sleep/food history ──
        if primary_intent in ("EMOTIONAL_STATE", "INFERENCE_REQUEST", "SYNTHESIS"):
            mood_logs = await pg_fetch("""
                SELECT date, mood, energy, stress, sleep_hours, sleep_quality
                FROM daily_logs
                WHERE mood IS NOT NULL
                ORDER BY date DESC, created_at DESC
                LIMIT 10
            """)
            result["mood_history"] = [
                {k: (str(v) if isinstance(v, (datetime,)) else v)
                 for k, v in m.items() if v is not None}
                for m in mood_logs
            ]

        # ── For TASK_PLANNING: pending tasks ranked by TWS ──
        if primary_intent in ("TASK_PLANNING", "SYNTHESIS", "FACTUAL_PERSONAL"):
            tasks = await pg_fetch("""
                SELECT title, faction, priority, urgency, difficulty,
                       tws, estimated_hours, deferral_count, status,
                       scheduled_date
                FROM tasks
                WHERE status IN ('pending', 'in_progress')
                ORDER BY tws DESC NULLS LAST
                LIMIT 8
            """)
            for t in tasks:
                if t.get("scheduled_date"):
                    t["scheduled_date"] = str(t["scheduled_date"])
            result["tasks"] = tasks

        # ── Faction scores (latest week) ──
        factions = await pg_fetch("""
            SELECT faction, actual_hours, target_hours, completion_rate
            FROM faction_stats
            WHERE week_start >= NOW() - INTERVAL '14 days'
            ORDER BY week_start DESC
            LIMIT 4
        """)
        if factions:
            result["faction_scores"] = factions

        # ── Mood trend (7d vs prior 7d) ──
        trend_row = await pg_fetchrow("""
            SELECT
                AVG(CASE WHEN date >= NOW() - INTERVAL '7 days' THEN mood END) AS recent_avg,
                AVG(CASE WHEN date < NOW() - INTERVAL '7 days'
                          AND date >= NOW() - INTERVAL '14 days' THEN mood END) AS prev_avg
            FROM daily_logs
            WHERE checkin_type = 'morning' AND mood IS NOT NULL
        """)
        if trend_row and trend_row.get("recent_avg") and trend_row.get("prev_avg"):
            diff = float(trend_row["recent_avg"]) - float(trend_row["prev_avg"])
            if diff > 0.5:
                result["mood_trend"] = "improving"
            elif diff < -0.5:
                result["mood_trend"] = "declining"
            else:
                result["mood_trend"] = "stable"

        # ── Behavioral events (recent) ──
        events = await pg_fetch("""
            SELECT event_type, entity_type, data, created_at
            FROM behavioral_events
            WHERE created_at >= NOW() - $1::interval
            ORDER BY created_at DESC
            LIMIT 10
        """, interval)
        for e in events:
            if e.get("created_at"):
                e["created_at"] = str(e["created_at"])
        result["behavioral_events"] = events

    except Exception as e:
        log.error(f"PostgreSQL retrieval failed: {e}")

    return result


# ═══════════════════════════════════════════════════════════════
#  NEO4J RETRIEVER — Direct driver queries
# ═══════════════════════════════════════════════════════════════

async def _fetch_neo4j(query: str, primary_intent: str) -> dict:
    """
    Traverse the behavioral knowledge graph for relevant patterns,
    traits, interests, and pathways.
    """
    result = {
        "traits": [],
        "patterns": [],
        "interests": [],
        "active_projects": [],
        "avoidances": [],
        "pathways": [],
    }

    try:
        from services.neo4j_service import get_driver
        driver = await get_driver()

        async with driver.session() as s:
            # ── Core personality data (always retrieved) ──
            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[rel:HAS_TRAIT]->(t:Trait) "
                "RETURN t.name AS name, coalesce(rel.confidence, 0.5) AS confidence "
                "ORDER BY confidence DESC LIMIT 8"
            )
            result["traits"] = [
                {"name": rec["name"], "confidence": rec["confidence"]}
                async for rec in r
            ]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:EXHIBITS_PATTERN]->(pat:Pattern) "
                "RETURN pat.description AS desc, coalesce(pat.strength, 1.0) AS strength, "
                "       pat.type AS type "
                "ORDER BY strength DESC LIMIT 6"
            )
            result["patterns"] = [
                {"description": rec["desc"], "strength": rec["strength"], "type": rec["type"]}
                async for rec in r
            ]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:INTERESTED_IN]->(i:Interest) "
                "RETURN i.name AS name "
                "ORDER BY coalesce(i.last_mentioned, datetime()) DESC LIMIT 10"
            )
            result["interests"] = [rec["name"] async for rec in r]

            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[:WORKING_ON]->(pr:Project {status:'active'}) "
                "RETURN pr.name AS name"
            )
            result["active_projects"] = [rec["name"] async for rec in r]

            # ── Avoidances (for behavioral queries) ──
            if primary_intent in ("BEHAVIORAL_PATTERN", "INFERENCE_REQUEST", "SYNTHESIS"):
                r = await s.run(
                    "MATCH (p:Person {name:'Shivam'})-[:AVOIDS]->(a:Avoidance) "
                    "RETURN a.description AS desc, coalesce(a.frequency, 1) AS freq "
                    "ORDER BY freq DESC LIMIT 5"
                )
                result["avoidances"] = [
                    {"description": rec["desc"], "frequency": rec["freq"]}
                    async for rec in r
                ]

            # ── Top weighted pathways (Hebbian) ──
            r = await s.run(
                "MATCH (p:Person {name:'Shivam'})-[r]->(n) "
                "WHERE r.weight IS NOT NULL "
                "RETURN type(r) AS rel_type, labels(n)[0] AS target_type, "
                "       coalesce(n.name, n.description, 'unnamed') AS target_name, "
                "       r.weight AS weight "
                "ORDER BY r.weight DESC LIMIT 10"
            )
            result["pathways"] = [
                {
                    "relationship": rec["rel_type"],
                    "target_type": rec["target_type"],
                    "target": rec["target_name"],
                    "weight": rec["weight"],
                }
                async for rec in r
            ]

    except Exception as e:
        log.error(f"Neo4j retrieval failed: {e}")

    return result


# ═══════════════════════════════════════════════════════════════
#  QDRANT RETRIEVER — Direct HTTP to Qdrant
# ═══════════════════════════════════════════════════════════════

async def _fetch_qdrant(query: str) -> list:
    """
    Semantic search against Qdrant locus_vault collection.
    Returns top 7 results with recency boost (1.5x for last 7 days).
    """
    try:
        from services.qdrant_service import get_embedding

        vector = await get_embedding(query)
        if not vector:
            return []

        payload = {
            "vector": vector,
            "limit": 10,  # over-fetch, then re-rank
            "with_payload": True,
            "score_threshold": 0.30,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{QDRANT_URL}/collections/locus_vault/points/search",
                json=payload
            )
            if r.status_code != 200:
                return []

            results = []
            cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()

            for pt in r.json().get("result", []):
                payload_data = pt.get("payload", {})
                score = pt.get("score", 0.0)

                # Recency boost: 1.5x for items modified in last 7 days
                modified = payload_data.get("file_modified_at", "")
                if modified and modified > cutoff_7d:
                    score *= 1.5

                results.append({
                    "score": round(score, 3),
                    "text": payload_data.get("chunk_text", payload_data.get("text", "")),
                    "filename": payload_data.get("file_path", payload_data.get("source_id", "")),
                    "tags": payload_data.get("tags", []),
                })

            # Sort by boosted score, take top 7
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:7]

    except Exception as e:
        log.error(f"Qdrant retrieval failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
#  OBSIDIAN/LIGHTRAG RETRIEVER
# ═══════════════════════════════════════════════════════════════

async def _fetch_obsidian(query: str) -> list:
    """
    1. Try LightRAG first (unified knowledge retrieval)
    2. Fall back to direct vault file search if LightRAG fails
    3. Always include recently modified notes that are semantically related
    """
    results = []

    # ── Try LightRAG ──
    try:
        from services.lightrag_service import query_brain
        rag_result = await query_brain(query, mode="hybrid")
        if rag_result.get("status") == "ok" and rag_result.get("answer"):
            results.append({
                "source": "lightrag",
                "content": rag_result["answer"][:500],
            })
    except Exception as e:
        log.warning(f"LightRAG query failed: {e}")

    # ── Direct vault search fallback / supplement ──
    try:
        from pathlib import Path
        vault_path = Path(VAULT_DIR)
        if vault_path.exists():
            # Find recently modified files (last 48h)
            cutoff = datetime.now().timestamp() - (48 * 3600)
            recent_files = []
            for md_file in vault_path.rglob("*.md"):
                if md_file.stat().st_mtime > cutoff:
                    recent_files.append(md_file)

            # Simple keyword matching on recent files
            query_words = set(query.lower().split())
            for rf in recent_files[:20]:
                try:
                    content = rf.read_text(errors="ignore")[:2000]
                    content_lower = content.lower()
                    # Check for keyword overlap
                    matches = sum(1 for w in query_words if len(w) > 3 and w in content_lower)
                    if matches >= 1:
                        results.append({
                            "source": f"vault:{rf.name}",
                            "content": content[:400],
                            "relevance": matches,
                        })
                except Exception:
                    pass

            # Sort by relevance
            results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    except Exception as e:
        log.warning(f"Vault direct search failed: {e}")

    return results[:5]


# ═══════════════════════════════════════════════════════════════
#  REDIS CACHE RETRIEVER
# ═══════════════════════════════════════════════════════════════

async def _fetch_redis_cache(query: str) -> dict:
    """
    Fetch cached state data from Redis:
    - CURRENT_STATE (psychological + operational state)
    - User identity layer
    - Faction scores
    """
    from core.db import redis_get_json

    result = {}

    try:
        # Current state (from state_engine)
        state = await redis_get_json("locus:current_state")
        if state:
            result["current_state"] = state

        # Groq token usage
        from core.db import redis_get_int
        tokens = await redis_get_int("groq_tokens_today")
        result["groq_tokens_today"] = tokens

    except Exception as e:
        log.warning(f"Redis cache fetch failed: {e}")

    return result


# ═══════════════════════════════════════════════════════════════
#  WEB SEARCH RETRIEVER — DuckDuckGo (free, no API key)
# ═══════════════════════════════════════════════════════════════

async def _fetch_web(query: str) -> list:
    """
    Free web search via DuckDuckGo Instant Answer API.
    Only invoked when sources_required includes 'web'.
    """
    results = []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            # DuckDuckGo Instant Answer API (free, no key)
            r = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }
            )
            if r.status_code == 200:
                data = r.json()

                # Abstract (main answer)
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", ""),
                        "snippet": data["Abstract"][:300],
                        "url": data.get("AbstractURL", ""),
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:3]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:80],
                            "snippet": topic.get("Text", "")[:200],
                            "url": topic.get("FirstURL", ""),
                        })

    except Exception as e:
        log.warning(f"Web search failed: {e}")

    return results[:3]


# ═══════════════════════════════════════════════════════════════
#  DISPATCHER — Parallel retrieval
# ═══════════════════════════════════════════════════════════════

async def parallel_retrieve(query: str, routing_info: dict) -> Dict[str, Any]:
    """
    Retrieve data from all sources specified in routing_info in parallel.
    Uses asyncio.gather for true parallel execution.

    Args:
        query: The user's natural language query.
        routing_info: Output of classify_query() — contains sources_required,
                      temporal_scope, primary_intent.

    Returns:
        Dict mapping source name → retrieved data.
    """
    sources = routing_info.get("sources_required", [])
    scope = routing_info.get("temporal_scope", "last_7d")
    primary_intent = routing_info.get("primary_intent", "SYNTHESIS")

    if not sources:
        sources = ["postgres", "neo4j", "qdrant", "obsidian", "redis_cache"]

    # Build coroutine map
    coro_map = {
        "postgres": _fetch_postgres(query, scope, primary_intent),
        "neo4j": _fetch_neo4j(query, primary_intent),
        "qdrant": _fetch_qdrant(query),
        "obsidian": _fetch_obsidian(query),
        "redis_cache": _fetch_redis_cache(query),
        "web": _fetch_web(query),
    }

    # Only launch requested sources
    tasks = {}
    for src in sources:
        if src in coro_map:
            tasks[src] = asyncio.create_task(coro_map[src])
        else:
            log.warning(f"Unknown source requested: {src}")

    # Await all in parallel
    results: Dict[str, Any] = {}
    for src, task in tasks.items():
        try:
            results[src] = await task
        except Exception as e:
            log.error(f"Source {src} failed: {e}")
            results[src] = {} if src not in ("qdrant", "obsidian", "web") else []

    return results
