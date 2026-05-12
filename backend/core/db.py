"""
db.py — Shared database connection pools for Locus core modules.

All core/ modules use these pools directly instead of HTTP round-trips
through the API. This eliminates the circular dependency problem and
makes retrieval 10x faster.
"""

import os
import asyncio
import logging
import json

log = logging.getLogger("locus-db")

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

# ── PostgreSQL Pool ──────────────────────────────────────────

_pg_pool = None
_pg_lock = asyncio.Lock()


async def get_pg_pool():
    """Get or create a shared asyncpg connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    async with _pg_lock:
        if _pg_pool is None:
            import asyncpg
            _pg_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=15,
            )
            log.info("PostgreSQL pool initialized")
        return _pg_pool


async def pg_fetch(query: str, *args):
    """Execute a SELECT and return rows as list of dicts."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def pg_fetchval(query: str, *args):
    """Execute a query and return a single value."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def pg_fetchrow(query: str, *args):
    """Execute a query and return a single row as dict."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def pg_execute(query: str, *args):
    """Execute a non-SELECT statement."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


# ── Redis ────────────────────────────────────────────────────

_redis_client = None
_redis_lock = asyncio.Lock()


async def get_redis():
    """Get or create a shared Redis client (async)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    async with _redis_lock:
        if _redis_client is None:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
            log.info("Redis async client initialized")
        return _redis_client


async def redis_get_json(key: str) -> dict | None:
    """Get a JSON value from Redis."""
    r = await get_redis()
    val = await r.get(key)
    if val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return None
    return None


async def redis_set_json(key: str, data: dict, ttl_seconds: int = 21600):
    """Set a JSON value in Redis with TTL (default 6 hours)."""
    r = await get_redis()
    await r.set(key, json.dumps(data, default=str), ex=ttl_seconds)


async def redis_incr(key: str, amount: int = 1) -> int:
    """Increment a Redis counter."""
    r = await get_redis()
    return await r.incrby(key, amount)


async def redis_get_int(key: str) -> int:
    """Get an integer from Redis (returns 0 if not set)."""
    r = await get_redis()
    val = await r.get(key)
    return int(val) if val else 0
