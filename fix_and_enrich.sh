#!/bin/bash
set -e

echo "=== Step 1: Fix docker-compose.yml — add Postgres port mapping ==="

cd /opt/locus

# Check if ports already added for postgres
if grep -A2 'container_name: locus-postgres' docker-compose.yml | grep -q 'ports:'; then
    echo "Postgres port mapping already exists, skipping..."
else
    # Use Python to safely edit the YAML since sed is fragile
    python3.11 << 'PYEOF'
import re

with open('/opt/locus/docker-compose.yml', 'r') as f:
    content = f.read()

# Find the postgres service healthcheck section and add ports after it
# We need to add ports: - "127.0.0.1:5432:5432" to the postgres service
old = """    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:"""

new = """    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:"""

if old in content:
    content = content.replace(old, new)
    with open('/opt/locus/docker-compose.yml', 'w') as f:
        f.write(content)
    print("  Added ports: 127.0.0.1:5432:5432 to postgres service")
else:
    print("  Could not find expected pattern — check docker-compose.yml manually")
    # Try to check if ports already there
    if '5432:5432' in content:
        print("  Ports mapping already present!")
    else:
        print("  ERROR: unexpected docker-compose.yml format")
        exit(1)
PYEOF
fi

echo ""
echo "=== Step 2: Recreate Postgres with port mapping ==="
docker compose up -d postgres
sleep 10
echo "Postgres status:"
docker compose ps postgres

echo ""
echo "=== Step 3: Test DB connection from host ==="
python3.11 << 'PYEOF'
import asyncio, asyncpg

async def test():
    conn = await asyncpg.connect(
        host='127.0.0.1',
        port=5432,
        user='locus',
        password='PostgreSQL@3301.Locus',
        database='locus'
    )
    version = await conn.fetchval('SELECT version()')
    print(f"  DB OK: {version[:60]}")
    
    # Check tables exist
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print(f"  Tables: {', '.join(t['tablename'] for t in tables)}")
    await conn.close()

asyncio.run(test())
PYEOF

echo ""
echo "=== Step 4: Deploy improved vault_enricher.py ==="
# The enricher needs to connect to localhost, not 'postgres' docker hostname
cat > /opt/locus/backend/services/vault_enricher.py << 'PYEOF'
import os, asyncio, httpx, asyncpg, json
from pathlib import Path
from datetime import datetime

GROQ_KEY = os.getenv("GROQ_API_KEY")
VAULT_PATH = "/vault"

# When running on host (not in Docker), connect via localhost
# When running in Docker, connect via 'postgres' hostname
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "locus")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "PostgreSQL@3301.Locus")
DB_NAME = os.getenv("POSTGRES_DB", "locus")

ENRICHMENT_PROMPT = """Analyze this personal note from Shivam Soni. Return JSON only:
{
  "entities": ["people, projects, tools, places"],
  "concepts": ["themes, ideas, topics"],
  "emotions": ["mood signals"],
  "connections": ["which areas: Monevo, Stratmore Guild, Locus, filmmaking, academics, family, philosophy"],
  "classification": "outcome|project|task|idea|resource|journal|noise",
  "classification_confidence": 0.0,
  "faction": "health|leverage|craft|expression|mixed|unknown",
  "task_if_applicable": {"action": "string", "estimated_hours": 1.0, "difficulty": 5, "urgency": 5, "priority": 5},
  "project_if_applicable": {"title": "string"},
  "enriched_summary": "2-3 sentences making thinking explicit",
  "tags": ["5 lowercase-hyphenated tags"],
  "contradictions": null
}
Return ONLY JSON. No markdown."""

async def get_db_conn():
    return await asyncpg.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME
    )

async def call_groq_70b(content):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "system", "content": ENRICHMENT_PROMPT},
                                {"role": "user", "content": content[:4000]}],
                  "temperature": 0.1, "response_format": {"type": "json_object"}}
        )
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])

async def enrich_file(file_path):
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if "## ⟨locus⟩" in content or len(content.strip()) < 20:
        return False
    print(f"Enriching: {file_path.name}")
    try:
        e = await call_groq_70b(content)
    except Exception as ex:
        print(f"  ERROR calling Groq: {ex}")
        return False
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    annotation = f"""

---

## ⟨locus⟩
*Auto-enriched: {timestamp}*

**Classification:** {e.get('classification','unknown')} ({e.get('classification_confidence',0):.0%})
**Faction:** {e.get('faction','unknown')}
**Entities:** {', '.join(e.get('entities',[])[:8])}
**Concepts:** {', '.join(e.get('concepts',[])[:6])}
**Connections:** {', '.join(e.get('connections',[]))}
**Tags:** {' '.join(['#'+t for t in e.get('tags',[])])}

**Summary:** {e.get('enriched_summary','')}
"""
    file_path.write_text(content + annotation, encoding="utf-8")
    
    conn = await get_db_conn()
    try:
        cls = e.get('classification')
        faction = e.get('faction','craft')
        if faction not in ('health','leverage','craft','expression'): faction = 'craft'
        if cls == 'task' and e.get('task_if_applicable'):
            t = e['task_if_applicable']
            if isinstance(t, dict) and t.get('action'):
                await conn.execute("""INSERT INTO tasks (user_id,title,description,faction,priority,urgency,difficulty,estimated_hours,status)
                    VALUES ('shivam',$1,$2,$3,$4,$5,$6,$7,'pending') ON CONFLICT DO NOTHING""",
                    t.get('action',file_path.stem)[:200], content[:500], faction,
                    min(10,max(1,int(t.get('priority',5)))), min(10,max(1,int(t.get('urgency',5)))),
                    min(10,max(1,int(t.get('difficulty',5)))), float(t.get('estimated_hours',1.0)))
                print(f"  → Task: {t.get('action','')[:60]}")
        elif cls == 'project' and e.get('project_if_applicable'):
            p = e['project_if_applicable']
            if isinstance(p, dict) and p.get('title'):
                await conn.execute("""INSERT INTO projects (user_id,title,description,faction,status)
                    VALUES ('shivam',$1,$2,$3,'active') ON CONFLICT DO NOTHING""",
                    p.get('title',file_path.stem)[:200], content[:500], faction)
                print(f"  → Project: {p.get('title','')[:60]}")
        await conn.execute("INSERT INTO behavioral_events (user_id,event_type,data) VALUES ('shivam','vault_enrich',$1)",
            json.dumps({"file":file_path.name,"classification":cls,"faction":e.get('faction')})[:500])
    finally:
        await conn.close()
    return True

async def run_enrichment():
    vault = Path(VAULT_PATH)
    files = list(vault.glob("00-Inbox/**/*.md")) + list(vault.glob("00-Inbox/**/*.txt"))
    print(f"Vault enricher: {len(files)} files")
    enriched = 0
    errors = 0
    for f in files:
        try:
            if await enrich_file(f):
                enriched += 1
                await asyncio.sleep(1)
        except Exception as ex:
            print(f"  ERROR on {f.name}: {ex}")
            errors += 1
    print(f"Done: {enriched}/{len(files)} enriched, {errors} errors")

if __name__ == "__main__":
    asyncio.run(run_enrichment())
PYEOF

echo "  Enricher deployed."

echo ""
echo "=== Step 5: Run enrichment ==="
echo "Starting vault enrichment on 55 inbox files..."
echo "(Each file ~3-5 sec via Groq 70b)"
echo ""

cd /opt/locus/backend
export GROQ_API_KEY=$(grep '^GROQ_API_KEY=' /opt/locus/.env | cut -d= -f2)
python3.11 services/vault_enricher.py

echo ""
echo "=== DONE ==="
echo "Check any vault file in Obsidian — you should see ## ⟨locus⟩ at the bottom."
