# /opt/locus/backend/services/vault_indexer_v2.py
# Proposition-based vault indexer.
#
# Replaces the old vault_enricher.py + index_vault.py.
# For every .md file in /vault/:
#   1. Proposition chunking (via proposition_chunker.py)
#   2. Embed and upsert to Qdrant (via qdrant_service.py)
#   3. Sync metadata to Neo4j + Postgres (via sync_layer.py)
#
# Runs: nightly at 11:30 PM + on-demand via /sync command

import os
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("locus-indexer-v2")

VAULT_PATH = os.getenv("VAULT_PATH", "/vault")

# Updated scan dirs to match ACTUAL vault folder structure on VM
VAULT_SCAN_DIRS = [
    "00-Inbox",
    "01-Journal",
    "02-Projects",
    "03-AI-Chats",
    "04-Resources",
    "05-Content",
]

# Track indexed files to support incremental indexing
_indexed_files: dict[str, str] = {}  # file_path -> last_modified_iso


async def _should_reindex(file_path: Path) -> bool:
    """Check if file needs re-indexing based on modification time."""
    mod_time = datetime.fromtimestamp(
        file_path.stat().st_mtime, tz=timezone.utc
    ).isoformat()
    key = str(file_path)
    if key in _indexed_files and _indexed_files[key] == mod_time:
        return False
    return True


async def index_file(file_path: Path, force: bool = False) -> dict:
    """
    Index a single vault file using proposition-based chunking.

    Returns: {
        "file": str,
        "chunks": int,
        "upserted": int,
        "synced": dict,
        "error": str or None,
    }
    """
    from services.proposition_chunker import chunk_file
    from services.qdrant_service import upsert_proposition_chunks, delete_file_points
    from services.sync_layer import sync_vault_note

    result = {
        "file": str(file_path),
        "chunks": 0,
        "upserted": 0,
        "synced": {},
        "error": None,
    }

    try:
        # Check if file needs re-indexing
        if not force and not await _should_reindex(file_path):
            result["error"] = "skipped (not modified)"
            return result

        # Step 1: Proposition chunking
        chunks = await chunk_file(file_path)
        result["chunks"] = len(chunks)

        if not chunks:
            result["error"] = "no propositions extracted"
            return result

        # Step 2: Delete old points for this file (clean re-index)
        await delete_file_points(str(file_path))

        # Step 3: Embed and upsert to Qdrant
        upserted = await upsert_proposition_chunks(chunks)
        result["upserted"] = upserted

        # Step 4: Sync metadata to Neo4j + Postgres
        # Extract metadata from the first chunk for the sync
        first_chunk = chunks[0]
        tags = first_chunk.get("tags", [])
        vault_section = first_chunk.get("vault_section", "unknown")

        sync_result = await sync_vault_note(
            file_path=str(file_path),
            vault_section=vault_section,
            tags=tags,
        )
        result["synced"] = sync_result

        # Update tracking
        mod_time = datetime.fromtimestamp(
            file_path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        _indexed_files[str(file_path)] = mod_time

        log.info(
            f"Indexed {file_path.name}: "
            f"{len(chunks)} chunks, {upserted} upserted, "
            f"sync={sync_result}"
        )

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Index error for {file_path.name}: {e}")

    return result


async def run_full_index(
    vault_path: str = VAULT_PATH,
    force: bool = False,
    max_files: int = 0,
) -> dict:
    """
    Full vault indexing job.

    Args:
        vault_path: Root vault directory
        force: Re-index even if file hasn't changed
        max_files: Limit files to process (0 = no limit)

    Returns: summary dict
    """
    vault = Path(vault_path)
    if not vault.exists():
        msg = f"Vault path '{vault_path}' does not exist"
        log.error(msg)
        return {"error": msg, "indexed": 0, "total": 0}

    # Collect all .md files from scan dirs
    files = []
    for folder in VAULT_SCAN_DIRS:
        folder_path = vault / folder
        if folder_path.exists():
            files += list(folder_path.rglob("*.md"))
        else:
            log.info(f"Vault scan dir not found: {folder}")

    # Deduplicate
    files = list({str(f): f for f in files}.values())

    # Apply max_files limit
    if max_files > 0:
        files = files[:max_files]

    log.info(f"Vault indexer v2: {len(files)} files found across {VAULT_SCAN_DIRS}")

    # Get current Qdrant stats
    from services.qdrant_service import collection_stats
    stats_before = await collection_stats()
    log.info(f"Qdrant before: {stats_before.get('points_count', 0)} points")

    # Process files
    indexed = 0
    failed = 0
    skipped = 0
    total_chunks = 0
    total_upserted = 0
    errors = []

    for i, f in enumerate(files, 1):
        if i % 50 == 0:
            log.info(f"Progress: {i}/{len(files)} files processed")

        result = await index_file(f, force=force)

        if result["error"]:
            if "skipped" in str(result["error"]):
                skipped += 1
            else:
                failed += 1
                errors.append(f"{f.name}: {result['error']}")
        else:
            indexed += 1
            total_chunks += result["chunks"]
            total_upserted += result["upserted"]

        # Rate limit: avoid overwhelming Groq API
        # (proposition classifier uses LLM calls)
        if result["chunks"] > 0:
            await asyncio.sleep(1.0)

    stats_after = await collection_stats()

    summary = {
        "total_files": len(files),
        "indexed": indexed,
        "failed": failed,
        "skipped": skipped,
        "total_chunks": total_chunks,
        "total_upserted": total_upserted,
        "qdrant_before": stats_before.get("points_count", 0),
        "qdrant_after": stats_after.get("points_count", 0),
        "errors": errors[:10],  # Cap at 10 errors in summary
    }

    log.info(
        f"Vault indexer v2 complete: "
        f"{indexed}/{len(files)} indexed, {failed} failed, {skipped} skipped, "
        f"Qdrant: {stats_before.get('points_count', 0)} → {stats_after.get('points_count', 0)} points"
    )

    return summary


async def run_incremental_index(vault_path: str = VAULT_PATH) -> dict:
    """
    Incremental indexing — only process new/modified files.
    This is the default for nightly runs.
    """
    return await run_full_index(vault_path=vault_path, force=False)


if __name__ == "__main__":
    asyncio.run(run_full_index(force=True))
