"""
vault.py — Vault management endpoints.

  POST /vault/enrich   → trigger enrichment + proposition indexing
  POST /vault/reindex  → force full re-index with proposition chunking
  GET  /vault/stats    → vault + Qdrant stats
  GET  /vault/health   → tri-store sync health
"""

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
import os
import logging

router = APIRouter()
log = logging.getLogger(__name__)

SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN", "")


def _check(token):
    if token != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/vault/enrich")
async def enrich_vault(
    background_tasks: BackgroundTasks,
    x_service_token: str = Header(None),
):
    """Trigger vault enrichment + proposition-based indexing in background."""
    _check(x_service_token)

    async def _run():
        try:
            # Phase 1: Proposition indexing
            from services.vault_indexer_v2 import run_incremental_index
            summary = await run_incremental_index()
            log.info(f"Vault index complete: {summary}")
        except Exception as e:
            log.error(f"Vault indexing failed: {e}")

        try:
            # Phase 2: Enrichment
            from services.vault_enricher import run_enrichment
            enriched = await run_enrichment()
            log.info(f"Vault enrichment complete: {enriched} files")
        except Exception as e:
            log.error(f"Vault enrichment failed: {e}")

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Vault indexing + enrichment started in background"}


@router.post("/vault/reindex")
async def reindex_vault(
    background_tasks: BackgroundTasks,
    max_files: int = 0,
    x_service_token: str = Header(None),
):
    """Force full re-index of vault with proposition chunking."""
    _check(x_service_token)

    async def _run():
        try:
            from services.vault_indexer_v2 import run_full_index
            summary = await run_full_index(force=True, max_files=max_files)
            log.info(f"Vault full reindex complete: {summary}")
        except Exception as e:
            log.error(f"Vault full reindex failed: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": f"Full vault re-index started (max_files={max_files or 'all'})"
    }


@router.get("/vault/stats")
async def vault_stats(x_service_token: str = Header(None)):
    """Get vault file counts and Qdrant collection stats."""
    _check(x_service_token)

    from pathlib import Path
    from services.qdrant_service import collection_stats

    vault = Path(os.getenv("VAULT_PATH", "/vault"))
    file_count = 0
    dir_counts = {}

    scan_dirs = [
        "00-Inbox", "01-Journal", "02-Projects",
        "03-AI-Chats", "04-Resources", "05-Content",
    ]

    for folder in scan_dirs:
        folder_path = vault / folder
        if folder_path.exists():
            count = len(list(folder_path.rglob("*.md")))
            dir_counts[folder] = count
            file_count += count

    qdrant = await collection_stats()

    return {
        "vault_files": file_count,
        "vault_dirs": dir_counts,
        "qdrant": qdrant,
        "coverage": round(qdrant.get("points_count", 0) / max(file_count, 1) * 100, 1),
    }


@router.get("/vault/health")
async def vault_health(x_service_token: str = Header(None)):
    """Check sync layer health across all three stores."""
    _check(x_service_token)

    from services.sync_layer import sync_health
    return await sync_health()
