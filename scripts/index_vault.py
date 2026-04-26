"""
index_vault.py — Qdrant-native vault indexer.
Run this once (or after big vault changes) to populate Qdrant.

Usage on VM:
  cd /opt/locus
  export $(grep -v '^#' .env | xargs)
  python3 scripts/index_vault.py
"""

import asyncio, os, sys, hashlib
from pathlib import Path

# Allow importing from backend/services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

VAULT_PATH   = os.getenv("VAULT_PATH", "/vault")
QDRANT_URL   = os.getenv("QDRANT_URL", "http://localhost:6333")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")

VAULT_SCAN_DIRS = [
    "00-Inbox", "01-Areas", "02-Projects", "03-Resources", "04-Archive"
]


async def main():
    from services.qdrant_service import upsert_document, collection_stats

    vault = Path(VAULT_PATH)
    if not vault.exists():
        print(f"ERROR: Vault path '{VAULT_PATH}' not found.")
        print("On the VM, vault should be at /vault (Syncthing mount).")
        return

    # Collect files
    files = []
    for folder in VAULT_SCAN_DIRS:
        p = vault / folder
        if p.exists():
            files += list(p.rglob("*.md")) + list(p.rglob("*.txt"))
        else:
            print(f"  [skip] {folder}/ not found")

    files = list({str(f): f for f in files}.values())
    print(f"\nFound {len(files)} files across vault folders.")

    stats_before = await collection_stats()
    print(f"Qdrant before: {stats_before.get('points_count', 0)} points\n")

    indexed = 0
    failed  = 0

    for i, f in enumerate(files, 1):
        content = f.read_text(encoding="utf-8", errors="ignore").strip()
        if len(content) < 20:
            continue

        # Strip existing locus annotations for embedding
        if "## ⟨locus⟩" in content:
            clean = content[:content.index("## ⟨locus⟩")].strip()
        else:
            clean = content

        # Metadata from filename
        relative = f.relative_to(vault)
        folder   = str(relative.parts[0]) if len(relative.parts) > 1 else "root"

        metadata = {
            "source":   str(f),
            "filename": f.name,
            "stem":     f.stem,
            "folder":   folder,
            "type":     "vault_note",
            "text":     clean[:2000],
        }

        ok = await upsert_document(str(f), clean[:4000], metadata)
        status = "✓" if ok else "✗"
        print(f"[{i}/{len(files)}] {status} {f.name[:60]}")

        if ok:
            indexed += 1
        else:
            failed += 1

        await asyncio.sleep(0.3)   # stay within Gemini embedding rate limits

    stats_after = await collection_stats()
    print(f"\nDone. Indexed: {indexed} | Failed: {failed}")
    print(f"Qdrant after: {stats_after.get('points_count', 0)} points")


if __name__ == "__main__":
    asyncio.run(main())
