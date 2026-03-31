from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)
from app.config import settings
import httpx
import uuid

client = QdrantClient(url=settings.QDRANT_URL)

COLLECTIONS = {
    "behavioral_logs": 768,
    "obsidian_notes": 768,
    "recommendations": 768,
}

def ensure_collections():
    """Create Qdrant collections if they don't exist."""
    existing = {c.name for c in client.get_collections().collections}
    for name, size in COLLECTIONS.items():
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )

async def embed_text(text: str) -> list[float] | None:
    """Generate embedding via Ollama nomic-embed-text."""
    if not text or len(text.strip()) < 3:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(f"{settings.OLLAMA_URL}/api/embeddings", json={
                "model": "nomic-embed-text",
                "prompt": text
            })
            if resp.status_code == 200:
                return resp.json().get("embedding")
    except Exception:
        pass
    return None

async def upsert_behavioral_event(event_id: str, user_id: str, content: str, payload: dict):
    """Store a behavioral event embedding in Qdrant."""
    embedding = await embed_text(content)
    if not embedding:
        return

    ensure_collections()
    client.upsert(
        collection_name="behavioral_logs",
        points=[PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, event_id)),
            vector=embedding,
            payload={"user_id": user_id, "event_id": event_id, **payload}
        )]
    )

async def search_behavioral_logs(user_id: str, query: str, limit: int = 10) -> list:
    """Semantic search over behavioral logs for a user."""
    embedding = await embed_text(query)
    if not embedding:
        return []

    results = client.search(
        collection_name="behavioral_logs",
        query_vector=embedding,
        query_filter=Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id))
        ]),
        limit=limit,
        with_payload=True
    )
    return [{"score": r.score, "payload": r.payload} for r in results]
