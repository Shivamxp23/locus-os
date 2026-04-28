# /opt/locus/backend/services/qdrant_service.py
# Qdrant vector store for Locus vault.
#
# Embedding: fastembed BAAI/bge-small-en-v1.5 (384-dim, local, no API key)
# Collection: locus_vault
# Payload schema: proposition-based chunks

import os
import logging
import hashlib
import asyncio
from typing import Optional

import httpx

log = logging.getLogger("locus-qdrant")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = "locus_vault"
VECTOR_DIM = 384  # BAAI/bge-small-en-v1.5 (runs locally, no API key)

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


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts. More efficient than one-by-one."""
    model = await _get_model()
    if model is None:
        return [[] for _ in texts]
    try:
        loop = asyncio.get_event_loop()
        truncated = [t[:8000] for t in texts]
        all_vecs = await loop.run_in_executor(
            None,
            lambda: [list(v) for v in model.embed(truncated)]
        )
        return [[float(x) for x in vec] for vec in all_vecs]
    except Exception as e:
        log.error(f"Batch embedding failed: {e}")
        return [[] for _ in texts]


# ── Collection bootstrap ─────────────────────────────────────────────────────

async def ensure_collection():
    """Create the locus_vault collection if it doesn't exist.
    If it exists with wrong dimensions, log a warning but don't drop it."""
    url = f"{QDRANT_URL}/collections/{COLLECTION}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        if r.status_code == 200:
            # Verify dimension matches
            info = r.json().get("result", {})
            existing_dim = info.get("config", {}).get("params", {}).get("vectors", {}).get("size")
            if existing_dim and existing_dim != VECTOR_DIM:
                log.error(
                    f"Qdrant dimension mismatch! Collection has {existing_dim} dims, "
                    f"but we need {VECTOR_DIM}. Delete and recreate the collection."
                )
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


async def recreate_collection():
    """Drop and recreate the collection. Use with caution."""
    async with httpx.AsyncClient(timeout=15) as client:
        # Delete
        await client.delete(f"{QDRANT_URL}/collections/{COLLECTION}")
        log.info(f"Qdrant: deleted collection '{COLLECTION}'")
        # Recreate
        payload = {
            "vectors": {
                "size": VECTOR_DIM,
                "distance": "Cosine"
            }
        }
        r = await client.put(
            f"{QDRANT_URL}/collections/{COLLECTION}",
            json=payload
        )
        if r.status_code in (200, 201):
            log.info(f"Qdrant: recreated collection '{COLLECTION}' ({VECTOR_DIM} dims)")
        else:
            log.error(f"Qdrant collection recreate failed: {r.text}")


# ── Stable ID ────────────────────────────────────────────────────────────────

def _stable_id(source: str) -> int:
    h = hashlib.md5(source.encode()).hexdigest()
    return int(h[:15], 16)


# ── Upsert (legacy — single document) ───────────────────────────────────────

async def upsert_document(source_id: str, text: str, metadata: dict) -> bool:
    """Embed text and upsert into locus_vault. Legacy API for compatibility."""
    await ensure_collection()

    vector = await get_embedding(text)
    if not vector:
        return False

    point_id = _stable_id(source_id)
    payload = {"source_id": source_id, "text": text[:2000], **metadata}

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


# ── Upsert proposition chunks ───────────────────────────────────────────────

async def upsert_proposition_chunks(chunks: list[dict]) -> int:
    """
    Upsert proposition-based chunks into Qdrant.

    Each chunk dict must have:
        file_path, vault_section, chunk_index, propositions,
        chunk_text, file_modified_at, tags, locus_managed

    Returns number of successfully upserted points.
    """
    if not chunks:
        return 0

    await ensure_collection()

    # Embed all chunk_text fields in batch
    texts = [c["chunk_text"] for c in chunks]
    vectors = await get_embeddings_batch(texts)

    # Build points
    points = []
    for chunk, vector in zip(chunks, vectors):
        if not vector:
            continue
        point_id = _stable_id(f"{chunk['file_path']}::chunk::{chunk['chunk_index']}")
        points.append({
            "id": point_id,
            "vector": vector,
            "payload": chunk,
        })

    if not points:
        return 0

    # Upsert in batches of 100
    upserted = 0
    batch_size = 100
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            body = {"points": batch}
            try:
                r = await client.put(
                    f"{QDRANT_URL}/collections/{COLLECTION}/points",
                    json=body
                )
                if r.status_code in (200, 201):
                    upserted += len(batch)
                else:
                    log.error(f"Qdrant batch upsert failed: {r.text}")
            except Exception as e:
                log.error(f"Qdrant batch upsert error: {e}")

    return upserted


# ── Delete points for a file ────────────────────────────────────────────────

async def delete_file_points(file_path: str) -> bool:
    """Delete all points belonging to a specific file_path."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            body = {
                "filter": {
                    "must": [
                        {"key": "file_path", "match": {"value": file_path}}
                    ]
                }
            }
            r = await client.post(
                f"{QDRANT_URL}/collections/{COLLECTION}/points/delete",
                json=body
            )
            return r.status_code in (200, 201)
    except Exception as e:
        log.error(f"Qdrant delete points error: {e}")
        return False


# ── Search ───────────────────────────────────────────────────────────────────

async def direct_search(query: str, limit: int = 6) -> list[dict]:
    """Semantic search over locus_vault."""
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
