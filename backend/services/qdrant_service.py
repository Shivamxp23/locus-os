import os
import httpx
import logging
import hashlib

log = logging.getLogger("locus-qdrant")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
GROQ_KEY   = os.getenv("GROQ_API_KEY")   # Used for embeddings
COLLECTION  = "locus_vault"
VECTOR_DIM  = 768   # nomic-embed-text-v1.5 output dimension


# ── Collection bootstrap ─────────────────────────────────────────────────────

async def ensure_collection():
    """Create the locus_vault collection if it doesn't exist."""
    url = f"{QDRANT_URL}/collections/{COLLECTION}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return  # already exists

        payload = {
            "vectors": {
                "size": VECTOR_DIM,
                "distance": "Cosine"
            }
        }
        r2 = await client.put(url, json=payload)
        if r2.status_code in (200, 201):
            log.info(f"Qdrant: created collection '{COLLECTION}'")
        else:
            log.error(f"Qdrant collection create failed: {r2.text}")


# ── Embedding ────────────────────────────────────────────────────────────────

async def get_embedding(text: str) -> list[float]:
    """Get 768-dim embedding via Groq nomic-embed-text-v1.5."""
    if not GROQ_KEY:
        log.warning("GROQ_API_KEY missing — embedding unavailable.")
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/embeddings",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "nomic-embed-text-v1_5",
                    "input": text[:8000]
                }
            )
            r.raise_for_status()
            return r.json()["data"][0]["embedding"]
    except Exception as e:
        log.error(f"Embedding failed: {e}")
        return []


# ── Stable ID from path/text ─────────────────────────────────────────────────

def _stable_id(source: str) -> int:
    """Deterministic integer ID from a string (file path or capture id)."""
    h = hashlib.md5(source.encode()).hexdigest()
    return int(h[:15], 16)   # fits in i64


# ── Upsert ───────────────────────────────────────────────────────────────────

async def upsert_document(
    source_id: str,
    text: str,
    metadata: dict,
) -> bool:
    """
    Embed `text` and upsert into locus_vault collection.

    Args:
        source_id: Stable string key (file path or capture UUID)
        text:      Content to embed
        metadata:  Arbitrary dict stored as Qdrant payload
    Returns:
        True on success, False on failure
    """
    await ensure_collection()

    vector = await get_embedding(text)
    if not vector:
        return False

    point_id = _stable_id(source_id)

    payload = {
        "source_id": source_id,
        "text": text[:2000],        # Store first 2k chars for retrieval
        **metadata
    }

    url = f"{QDRANT_URL}/collections/{COLLECTION}/points"
    body = {
        "points": [{
            "id": point_id,
            "vector": vector,
            "payload": payload,
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.put(url, json=body)
            if r.status_code in (200, 201):
                return True
            else:
                log.error(f"Qdrant upsert failed ({source_id}): {r.text}")
                return False
    except Exception as e:
        log.error(f"Qdrant upsert error ({source_id}): {e}")
        return False


# ── Search ───────────────────────────────────────────────────────────────────

async def direct_search(query: str, limit: int = 6) -> list[dict]:
    """Semantic search over locus_vault."""
    await ensure_collection()

    vector = await get_embedding(query)
    if not vector:
        return []

    url = f"{QDRANT_URL}/collections/{COLLECTION}/points/search"
    payload = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "score_threshold": 0.4,     # Filter out very low relevance hits
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                results = []
                for pt in r.json().get("result", []):
                    results.append({
                        "id": pt.get("id"),
                        "score": round(pt.get("score", 0), 3),
                        "payload": pt.get("payload", {}),
                    })
                return results
            else:
                log.error(f"Qdrant search failed: {r.text}")
                return []
    except Exception as e:
        log.error(f"Qdrant search error: {e}")
        return []


# ── Collection stats ─────────────────────────────────────────────────────────

async def collection_stats() -> dict:
    """Return basic stats about the vault collection."""
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
