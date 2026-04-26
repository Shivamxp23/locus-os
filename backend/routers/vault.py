from fastapi import APIRouter, BackgroundTasks
from services.qdrant_service import direct_search, collection_stats
import logging
import os

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/vault/search")
async def vault_search(q: str = "", limit: int = 6):
    """Semantic search over the Obsidian vault via Qdrant."""
    if not q:
        return {"results": [], "query": q}
    results = await direct_search(q, limit=limit)
    return {"results": results, "query": q, "count": len(results)}


@router.get("/vault/health")
async def vault_health():
    stats = await collection_stats()
    return {"qdrant": stats}


@router.post("/vault/enrich")
async def trigger_enrichment(background_tasks: BackgroundTasks):
    """
    Trigger a full vault enrichment + Qdrant indexing pass.
    Returns immediately — job runs in the background.
    """
    background_tasks.add_task(_run_enrichment_job)
    return {"status": "started", "message": "Vault enrichment job started in background."}


async def _run_enrichment_job():
    try:
        from services.vault_enricher import run_enrichment
        count = await run_enrichment()
        log.info(f"Background enrichment complete: {count} files processed")
    except Exception as e:
        log.error(f"Background enrichment failed: {e}")
