# /opt/locus/backend/services/vault_change_tracker.py
# Tracks daily changes in Obsidian vault for logging to behavioral_events + Neo4j

import os
import json
import hashlib
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("vault-change-tracker")

VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
STATE_FILE = os.path.join(VAULT_PATH, ".locus", "vault_state.json")


def _ensure_state_dir():
    os.makedirs(os.path.join(VAULT_PATH, ".locus"), exist_ok=True)


def _load_state() -> dict:
    _ensure_state_dir()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_sync": None, "files": {}}


def _save_state(state: dict):
    _ensure_state_dir()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _file_hash(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def _scan_vault() -> dict[str, str]:
    files = {}
    vault_path = Path(VAULT_PATH)
    for f in vault_path.rglob("*.md"):
        rel_path = str(f.relative_to(vault_path))
        # Skip system folders
        if rel_path.startswith(".obsidian") or rel_path.startswith(".stversions"):
            continue
        files[rel_path] = _file_hash(f)
    return files


def detect_changes() -> dict:
    """
    Detect changes since last sync.
    Returns:
    {
        "added": ["file1.md", "file2.md"],
        "modified": ["file3.md"],
        "deleted": ["file4.md"],
        "unchanged": ["file5.md"],
        "timestamp": "2026-04-28T12:00:00"
    }
    """
    current_files = _scan_vault()
    state = _load_state()
    last_files = state.get("files", {})
    
    changes = {
        "added": [],
        "modified": [],
        "deleted": [],
        "unchanged": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Detect added and modified
    for path, file_hash in current_files.items():
        if path not in last_files:
            changes["added"].append(path)
        elif last_files[path] != file_hash:
            changes["modified"].append(path)
        else:
            changes["unchanged"].append(path)
    
    # Detect deleted
    for path in last_files:
        if path not in current_files:
            changes["deleted"].append(path)
    
    # Save new state
    state["files"] = current_files
    state["last_sync"] = changes["timestamp"]
    _save_state(state)
    
    log.info(f"Vault changes: {len(changes['added'])} added, {len(changes['modified'])} modified, {len(changes['deleted'])} deleted")
    return changes


def get_daily_summary() -> str:
    """Get a human-readable summary of today's changes."""
    changes = detect_changes()
    
    lines = [f"# Vault Changes - {date.today()}"]
    
    if not changes["added"] and not changes["modified"] and not changes["deleted"]:
        lines.append("No changes detected today.")
        return "\n".join(lines)
    
    if changes["added"]:
        lines.append(f"\n## Added ({len(changes['added'])})")
        for f in sorted(changes["added"])[:10]:
            lines.append(f"- {f}")
        if len(changes["added"]) > 10:
            lines.append(f"  ... and {len(changes['added']) - 10} more")
    
    if changes["modified"]:
        lines.append(f"\n## Modified ({len(changes['modified'])})")
        for f in sorted(changes["modified"])[:10]:
            lines.append(f"- {f}")
        if len(changes["modified"]) > 10:
            lines.append(f"  ... and {len(changes['modified']) - 10} more")
    
    if changes["deleted"]:
        lines.append(f"\n## Deleted ({len(changes['deleted'])})")
        for f in sorted(changes["deleted"])[:5]:
            lines.append(f"- {f}")
    
    return "\n".join(lines)


def get_change_log(limit: int = 7) -> list[dict]:
    """Get change logs for the last N syncs (stored in behavioral_events)."""
    # This requires the changes to be logged to Postgres
    # Placeholder - actual implementation would query behavioral_events
    return []


async def log_changes_to_db(changes: dict) -> bool:
    """Log vault changes to behavioral_events table."""
    import asyncpg
    
    if not changes["added"] and not changes["modified"] and not changes["deleted"]:
        return True
    
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string:
        log.warning("No DATABASE_URL - skipping DB log")
        return False
    
    try:
        conn = await asyncpg.connect(conn_string)
        
        summary = {
            "added_count": len(changes["added"]),
            "modified_count": len(changes["modified"]),
            "deleted_count": len(changes["deleted"]),
            "files": {
                "added": changes["added"],
                "modified": changes["modified"],
                "deleted": changes["deleted"]
            }
        }
        
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, "shivam", "vault_changes", json.dumps(summary))
        
        await conn.close()
        log.info(f"Logged vault changes to DB: {len(changes['added'])} added, {len(changes['modified'])} modified")
        return True
    except Exception as e:
        log.error(f"Failed to log vault changes: {e}")
        return False