import os
import httpx
import logging

log = logging.getLogger("locus-qdrant")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

async def get_embedding(text: str) -> list[float]:
    """Get embedding vector via Gemini"""
    if not GEMINI_KEY:
        log.warning("GEMINI_API_KEY missing for embedding.")
        return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_KEY}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text}]}
            })
            r.raise_for_status()
            return r.json()["embedding"]["values"]
    except Exception as e:
        log.error(f"Embedding failed: {e}")
        return []

async def direct_search(query: str, limit: int = 5) -> list[dict]:
    """Search Qdrant locus_vault natively"""
    vector = await get_embedding(query)
    if not vector:
        return []

    url = f"{QDRANT_URL}/collections/locus_vault/points/search"
    payload = {
        "vector": vector,
        "limit": limit,
        "with_payload": True
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                data = r.json()
                results = []
                for pt in data.get("result", []):
                    results.append({
                        "id": pt.get("id"),
                        "score": pt.get("score"),
                        "payload": pt.get("payload", {})
                    })
                return results
            else:
                log.error(f"Qdrant error: {r.text}")
                return []
    except Exception as e:
        log.error(f"Qdrant search failed: {e}")
        return []
