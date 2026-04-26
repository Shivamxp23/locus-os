import os
import logging
import hashlib
import asyncio

log = logging.getLogger("locus-qdrant")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION  = "locus_vault"
VECTOR_DIM  = 384   # BAAI/bge-small-en-v1.5 (runs locally, no API key)

# Lazy-loaded fastembed model
_model = None
_model_lock = asyncio.Lock()


# ── Embedding (local, no API key) ────────────────────────────────────────────

async def _get_model():
    global _model
    if _model is not None:
        return _model
    async with _model_lock:
        if _model is not None:
            return _model
        try:
            from fastembed import TextEmbedding
            _model = TextEmbedding("BAAI/bge-small-en-v1.5")
            log.info("FastEmbed model loaded: BAAI/bge-small-en-v1.5")
        except ImportError:
            log.error("fastembed not installed. Run: pip install fastembed")
            _model = None
    return _model


async def get_embedding(text: str) -> list[float]:
    """Get 384-dim local embedding via fastembed (BAAI/bge-small-en-v1.5)."""
    model = await _get_model()
    if model is None:
        return []
    try:
        # fastembed is synchronous; run in thread pool
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,
            lambda: list(model.embed([text[:8000]]))[0]
        )
        return [float(v) for v in vectors]
    except Exception as e:
        log.error(f"Embedding failed: {e}")
        return []


# ── Collection bootstrap ─────────────────────────────────────────────────────

async def ensure_collection():
    """Create the locus_vault collection if it doesn't exist."""
    import httpx
    url = f"{QDRANT_URL}/collections/{COLLECTION}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return

        payload = {
            "vectors": {
                "size": VECTOR_DIM,
                "distance": "Cosine"
            }
        }
        r2 = await client.put(url, json=payload)
        if r2.status_code in (200, 201):
            log.info(f"Qdrant: created collection '{COLLECTION}' ({VECTOR_DIM} dims)")
        else:
            log.error(f"Qdrant collection create failed: {r2.text}")


# ── Stable ID ────────────────────────────────────────────────────────────────

def _stable_id(source: str) -> int:
    h = hashlib.md5(source.encode()).hexdigest()
    return int(h[:15], 16)


# ── Upsert ───────────────────────────────────────────────────────────────────

async def upsert_document(source_id: str, text: str, metadata: dict) -> bool:
    """Embed text and upsert into locus_vault."""
    import httpx
    await ensure_collection()

    vector = await get_embedding(text)
    if not vector:
        return False

    point_id = _stable_id(source_id)
    payload  = {"source_id": source_id, "text": text[:2000], **metadata}

    body = {"points": [{"id": point_id, "vector": vector, "payload": payload}]}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION}/points",
                json=body
            )
            return r.status_code in (200, 201)
    except Exception as e:
        log.error(f"Qdrant upsert error ({source_id}): {e}")
        return False


# ── Search ───────────────────────────────────────────────────────────────────

async def direct_search(query: str, limit: int = 6) -> list[dict]:
    """Semantic search over locus_vault."""
    import httpx
    await ensure_collection()

    vector = await get_embedding(query)
    if not vector:
        return []

    payload = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "score_threshold": 0.35,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
                json=payload
            )
            if r.status_code == 200:
                return [
                    {"id": pt["id"], "score": round(pt["score"], 3), "payload": pt.get("payload", {})}
                    for pt in r.json().get("result", [])
                ]
    except Exception as e:
        log.error(f"Qdrant search error: {e}")
    return []


# ── Stats ─────────────────────────────────────────────────────────────────────

async def collection_stats() -> dict:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{QDRANT_URL}/collections/{COLLECTION}")
            if r.status_code == 200:
                info = r.json().get("result", {})
                return {
                    "points_count": info.get("points_count", 0),
                    "status": info.get("status", "unknown"),
                }
    except Exception as e:
        log.warning(f"Qdrant stats failed: {e}")
    return {"points_count": 0, "status": "unreachable"}
