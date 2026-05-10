"""
source_retriever.py — Parallel data source retriever for Locus System 1.

Retrieves context from multiple backends (Postgres, Neo4j, Qdrant,
Obsidian/Syncthing vault, Redis cache, Web) in parallel based on
the routing_info produced by query_classifier.
"""

import os
import asyncio
import json
import logging
from typing import Dict, Any

import httpx

log = logging.getLogger("locus-source-retriever")

API_URL = os.getenv("LOCUS_API_URL", "http://localhost:8000")
SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")
API_HEADERS = {"X-Service-Token": SERVICE_TOKEN}

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")


# ── Individual source fetchers ──────────────────────────────────

async def _fetch_postgres(query: str, scope: str) -> dict:
    """Fetch recent events from Postgres via the context API."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{API_URL}/api/v1/context/recent_behavior",
                headers=API_HEADERS,
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        log.warning(f"Postgres fetch failed: {e}")
    return {}


async def _fetch_neo4j(query: str) -> dict:
    """Fetch personality / graph pathways from Neo4j via the context API."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"{API_URL}/api/v1/context/personality",
                headers=API_HEADERS,
            )
            if r.status_code == 200:
                data = r.json()
                # Reshape into the format context_synthesizer expects
                return {"pathways": data.get("patterns", []), **data}
    except Exception as e:
        log.warning(f"Neo4j fetch failed: {e}")
    return {}


async def _fetch_qdrant(query: str) -> list:
    """Semantic search against Qdrant for relevant vault chunks."""
    try:
        # Use the vector search endpoint exposed by the API
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{API_URL}/api/v1/vector/search",
                json={"query": query, "limit": 5},
                headers=API_HEADERS,
            )
            if r.status_code == 200:
                return r.json().get("results", [])
    except Exception as e:
        log.warning(f"Qdrant fetch failed: {e}")
    return []


async def _fetch_obsidian(query: str) -> list:
    """Search Obsidian vault notes via the brain retriever endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{API_URL}/api/v1/brain/search",
                json={"query": query, "top_k": 5},
                headers=API_HEADERS,
            )
            if r.status_code == 200:
                return r.json().get("results", [])
    except Exception as e:
        log.warning(f"Obsidian fetch failed: {e}")
    return []


async def _fetch_redis_cache(query: str) -> dict:
    """Fetch cached identity / shorthand context from Redis."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{API_URL}/api/v1/context/brain_dump",
                headers=API_HEADERS,
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "identity": {
                        "personality": data.get("personality", {}),
                        "today": data.get("today", {}),
                    }
                }
    except Exception as e:
        log.warning(f"Redis cache fetch failed: {e}")
    return {}


async def _fetch_web(query: str) -> list:
    """Optional web search — currently a stub. Returns empty by default."""
    # Web search can be wired in later (e.g. Tavily, SerpAPI, etc.)
    return []


# ── Dispatcher map ──────────────────────────────────────────────

_SOURCE_MAP = {
    "postgres":    lambda q, s: _fetch_postgres(q, s),
    "neo4j":       lambda q, s: _fetch_neo4j(q),
    "qdrant":      lambda q, s: _fetch_qdrant(q),
    "obsidian":    lambda q, s: _fetch_obsidian(q),
    "redis_cache": lambda q, s: _fetch_redis_cache(q),
    "web":         lambda q, s: _fetch_web(q),
}


async def parallel_retrieve(query: str, routing_info: dict) -> Dict[str, Any]:
    """
    Retrieve data from all sources specified in routing_info in parallel.

    Args:
        query: The user's natural language query.
        routing_info: Output of classify_query(), containing 'sources_required'
                      and 'temporal_scope'.

    Returns:
        Dict mapping source name → retrieved data (dict or list).
    """
    sources = routing_info.get("sources_required", [])
    scope = routing_info.get("temporal_scope", "last_7d")

    if not sources:
        # Fallback: query everything
        sources = list(_SOURCE_MAP.keys())

    tasks = {}
    for src in sources:
        fetcher = _SOURCE_MAP.get(src)
        if fetcher:
            tasks[src] = asyncio.create_task(fetcher(query, scope))
        else:
            log.warning(f"Unknown source requested: {src}")

    results: Dict[str, Any] = {}
    for src, task in tasks.items():
        try:
            results[src] = await task
        except Exception as e:
            log.error(f"Source {src} failed: {e}")
            results[src] = {} if src not in ("qdrant", "obsidian", "web") else []

    return results
