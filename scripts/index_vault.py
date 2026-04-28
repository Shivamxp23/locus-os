"""
index_vault.py — Proposition-based vault indexer (v2).
Run this once (or after big vault changes) to populate Qdrant.

Usage on VM:
  cd /opt/locus
  export $(grep -v '^#' .env | xargs)
  python3 scripts/index_vault.py              # incremental
  python3 scripts/index_vault.py --force      # full re-index
  python3 scripts/index_vault.py --max 50     # limit to 50 files
"""

import asyncio, os, sys, argparse

# Allow importing from backend/services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def main(force: bool = False, max_files: int = 0):
    from services.vault_indexer_v2 import run_full_index
    from services.qdrant_service import collection_stats

    print("=" * 60)
    print("  Locus Vault Indexer v2 — Proposition-based Chunking")
    print("=" * 60)

    stats_before = await collection_stats()
    print(f"\nQdrant before: {stats_before.get('points_count', 0)} points")
    print(f"Force re-index: {force}")
    print(f"Max files: {max_files or 'all'}")
    print()

    summary = await run_full_index(force=force, max_files=max_files)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total files found:   {summary.get('total_files', 0)}")
    print(f"  Indexed:             {summary.get('indexed', 0)}")
    print(f"  Skipped (unchanged): {summary.get('skipped', 0)}")
    print(f"  Failed:              {summary.get('failed', 0)}")
    print(f"  Total chunks:        {summary.get('total_chunks', 0)}")
    print(f"  Total upserted:      {summary.get('total_upserted', 0)}")
    print(f"  Qdrant before:       {summary.get('qdrant_before', 0)}")
    print(f"  Qdrant after:        {summary.get('qdrant_after', 0)}")

    errors = summary.get("errors", [])
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:10]:
            print(f"    - {e}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Locus Vault Indexer v2")
    parser.add_argument("--force", action="store_true", help="Force re-index all files")
    parser.add_argument("--max", type=int, default=0, help="Max files to process (0=all)")
    args = parser.parse_args()
    asyncio.run(main(force=args.force, max_files=args.max))
