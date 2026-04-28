# /opt/locus/backend/services/vault_enricher.py
# Runs nightly + on-demand.
# For every new/changed vault file:
#   1. Read raw content
#   2. Call Groq 70b to extract entities, classify, enrich
#   3. Append ## ⟨locus⟩ section to the same file
#   4. Index into Qdrant (semantic search)
#   5. If Goal/Project/Task detected: write to PostgreSQL

import os
import asyncio
import httpx
import asyncpg
from pathlib import Path
from datetime import datetime
import json
import re

GROQ_KEY     = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
VAULT_PATH   = "/vault"

# Scan these folders (relative to VAULT_PATH)
VAULT_SCAN_DIRS = [
    "00-Inbox",
    "01-Journal",
    "02-Projects",
    "03-AI-Chats",
    "04-Resources",
    "05-Content",
]

ENRICHMENT_PROMPT = """You are analyzing a personal note from Shivam Soni — a 20-something building a startup, interested in filmmaking, philosophy, and self-optimization.

Read this note and return a JSON object with EXACTLY these fields:

{
  "entities": ["list of people, projects, tools, places mentioned"],
  "concepts": ["themes, ideas, topics"],
  "emotions": ["mood signals detected: curiosity, frustration, excitement, etc"],
  "connections": ["which of Shivam's known areas this connects to: Monevo, Stratmore Guild, Locus, filmmaking, academics, family, philosophy"],
  "classification": "ONE OF: outcome | project | task | idea | resource | journal | noise",
  "classification_confidence": 0.0-1.0,
  "outcome_if_applicable": "if classification is outcome: what life outcome does this represent? else null",
  "project_if_applicable": "if classification is project: what is the project title and which outcome does it serve? else null",
  "task_if_applicable": "if classification is task: what is the atomic action, estimated hours (float), difficulty 1-10, urgency 1-10, priority 1-10, which faction (health/leverage/craft/expression)? else null",
  "faction": "ONE OF: health | leverage | craft | expression | mixed | unknown",
  "action_potential": true/false,
  "enriched_summary": "2-3 sentences making Shivam's actual thinking explicit, not just describing the note",
  "tags": ["5 most relevant lowercase-hyphenated tags"],
  "contradictions": "anything that contradicts Shivam's stated goals or past behavior? null if none"
}

Return ONLY the JSON. No explanation. No markdown fences."""


async def call_groq_70b(content: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": ENRICHMENT_PROMPT},
                    {"role": "user", "content": content[:4000]}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
        )
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])


async def already_enriched(file_path: Path) -> bool:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    return "## ⟨locus⟩" in content


async def get_raw_content(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if "## ⟨locus⟩" in content:
        content = content[:content.index("## ⟨locus⟩")].strip()
    return content


async def append_enrichment(file_path: Path, raw_content: str, enrichment: dict):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    annotation = f"""

---

## ⟨locus⟩
*Auto-enriched: {timestamp}*

**Classification:** {enrichment.get('classification', 'unknown')} (confidence: {enrichment.get('classification_confidence', 0):.0%})
**Faction:** {enrichment.get('faction', 'unknown')}
**Entities:** {', '.join(enrichment.get('entities', [])[:8])}
**Concepts:** {', '.join(enrichment.get('concepts', [])[:6])}
**Connections:** {', '.join(enrichment.get('connections', []))}
**Tags:** {' '.join(['#' + t for t in enrichment.get('tags', [])])}

**Summary:** {enrichment.get('enriched_summary', '')}
"""

    if enrichment.get('contradictions'):
        annotation += f"\n**⚠️ Contradiction:** {enrichment['contradictions']}\n"

    if enrichment.get('task_if_applicable'):
        t = enrichment['task_if_applicable']
        if isinstance(t, dict):
            annotation += f"\n**→ Task Detected:** {t.get('action', '')} (Est: {t.get('estimated_hours', '?')}h, Priority: {t.get('priority', '?')}/10)\n"

    full_content = raw_content + annotation
    file_path.write_text(full_content, encoding="utf-8")


async def write_to_postgres_if_task(enrichment: dict, file_path: Path, raw_content: str):
    classification = enrichment.get('classification')
    if not DATABASE_URL:
        return
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        if classification == 'task' and enrichment.get('task_if_applicable'):
            t = enrichment.get('task_if_applicable', {})
            if isinstance(t, dict) and t.get('action'):
                faction = enrichment.get('faction', 'craft')
                if faction not in ('health', 'leverage', 'craft', 'expression'):
                    faction = 'craft'

                await conn.execute("""
                    INSERT INTO tasks (
                        user_id, title, description, faction,
                        priority, urgency, difficulty, estimated_hours, status
                    ) VALUES ('shivam', $1, $2, $3, $4, $5, $6, $7, 'pending')
                    ON CONFLICT DO NOTHING
                """,
                t.get('action', file_path.stem)[:200],
                raw_content[:500],
                faction,
                min(10, max(1, int(t.get('priority', 5)))),
                min(10, max(1, int(t.get('urgency', 5)))),
                min(10, max(1, int(t.get('difficulty', 5)))),
                float(t.get('estimated_hours', 1.0))
                )
                print(f"  → Task written to DB: {t.get('action', '')[:60]}")

        elif classification == 'project' and enrichment.get('project_if_applicable'):
            p = enrichment.get('project_if_applicable', {})
            if isinstance(p, dict) and p.get('title'):
                faction = enrichment.get('faction', 'craft')
                if faction not in ('health', 'leverage', 'craft', 'expression'):
                    faction = 'craft'

                await conn.execute("""
                    INSERT INTO projects (user_id, title, description, faction, status)
                    VALUES ('shivam', $1, $2, $3, 'active')
                    ON CONFLICT DO NOTHING
                """,
                p.get('title', file_path.stem)[:200],
                raw_content[:500],
                faction
                )
                print(f"  → Project written to DB: {p.get('title', '')[:60]}")

        # Always write behavioral event
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ('shivam', 'vault_enrich', $1)
        """, json.dumps({
            "file": file_path.name,
            "classification": classification,
            "faction": enrichment.get('faction'),
            "tags": enrichment.get('tags', [])
        })[:1000])

    finally:
        await conn.close()


async def index_to_qdrant(file_path: Path, raw_content: str, enrichment: dict) -> bool:
    """Index the enriched note into Qdrant for semantic search."""
    try:
        from services.qdrant_service import upsert_document

        # Build a rich text blob: raw content + enriched summary
        summary = enrichment.get("enriched_summary", "")
        tags    = " ".join(enrichment.get("tags", []))
        index_text = f"{raw_content[:2000]}\n\nSummary: {summary}\nTags: {tags}"

        metadata = {
            "source":         str(file_path),
            "filename":       file_path.name,
            "classification": enrichment.get("classification", "unknown"),
            "faction":        enrichment.get("faction", "unknown"),
            "tags":           enrichment.get("tags", []),
            "entities":       enrichment.get("entities", [])[:10],
            "concepts":       enrichment.get("concepts", [])[:8],
            "summary":        summary,
            "type":           "vault_note",
        }

        ok = await upsert_document(str(file_path), index_text, metadata)
        if ok:
            print(f"  → Indexed in Qdrant: {file_path.name}")
        else:
            print(f"  → Qdrant index failed: {file_path.name}")
        return ok

    except Exception as e:
        print(f"  → Qdrant index error ({file_path.name}): {e}")
        return False


async def enrich_file(file_path: Path) -> bool:
    try:
        raw_content = await get_raw_content(file_path)
        if len(raw_content.strip()) < 20:
            return False  # Skip nearly empty files

        already = await already_enriched(file_path)

        print(f"{'Re-enriching' if already else 'Enriching'}: {file_path.name}")
        enrichment = await call_groq_70b(raw_content)

        if not already:
            await append_enrichment(file_path, raw_content, enrichment)
            await write_to_postgres_if_task(enrichment, file_path, raw_content)

        # Always (re-)index into Qdrant — idempotent upsert
        await index_to_qdrant(file_path, raw_content, enrichment)

        print(f"  → {enrichment.get('classification')} | {enrichment.get('faction')} | {', '.join(enrichment.get('tags', [])[:3])}")
        return True

    except Exception as e:
        print(f"  ERROR enriching {file_path.name}: {e}")
        return False


async def run_enrichment(vault_path: str = VAULT_PATH) -> int:
    """Main enrichment job — runs nightly or on demand.
    Scans all configured vault folders and enriches + indexes each file."""
    vault = Path(vault_path)

    if not vault.exists():
        print(f"Vault path '{vault_path}' does not exist — skipping enrichment.")
        return 0

    files = []
    for folder in VAULT_SCAN_DIRS:
        folder_path = vault / folder
        if folder_path.exists():
            files += list(folder_path.rglob("*.md"))
            files += list(folder_path.rglob("*.txt"))

    # Deduplicate (in case of symlinks etc)
    files = list({str(f): f for f in files}.values())

    print(f"Vault enricher: {len(files)} files found across {VAULT_SCAN_DIRS}")
    enriched = 0

    for f in files:
        result = await enrich_file(f)
        if result:
            enriched += 1
            await asyncio.sleep(1)  # Rate limit: 1 file/sec

    print(f"Vault enricher complete: {enriched}/{len(files)} files processed")
    return enriched


if __name__ == "__main__":
    asyncio.run(run_enrichment())
