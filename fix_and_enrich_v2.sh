#!/bin/bash
set -e

echo "=== Step 1: Create DB tables ==="
# Run init.sql inside the postgres container
docker exec locus-postgres psql -U locus -d locus << 'SQLEOF'
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    checkin_type TEXT CHECK (checkin_type IN ('morning','evening')),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    energy INT CHECK (energy BETWEEN 1 AND 10),
    focus INT CHECK (focus BETWEEN 1 AND 10),
    stress INT CHECK (stress BETWEEN 1 AND 10),
    sleep_hours FLOAT,
    sleep_quality INT CHECK (sleep_quality BETWEEN 1 AND 5),
    exercise_minutes INT DEFAULT 0,
    journal TEXT,
    wins TEXT[],
    blockers TEXT[],
    tomorrow_plan TEXT[],
    faction_time JSONB DEFAULT '{"health":0,"leverage":0,"craft":0,"expression":0}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date, checkin_type)
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    priority INT DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    urgency INT DEFAULT 5 CHECK (urgency BETWEEN 1 AND 10),
    difficulty INT DEFAULT 5 CHECK (difficulty BETWEEN 1 AND 10),
    estimated_hours FLOAT DEFAULT 1.0,
    actual_hours FLOAT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','active','done','dropped','deferred')),
    scheduled_date DATE,
    completed_at TIMESTAMPTZ,
    parent_project_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    title TEXT NOT NULL,
    description TEXT,
    faction TEXT CHECK (faction IN ('health','leverage','craft','expression')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','completed','abandoned')),
    start_date DATE DEFAULT CURRENT_DATE,
    target_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS behavioral_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    event_type TEXT NOT NULL,
    data TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    interface TEXT CHECK (interface IN ('telegram','pwa')),
    interaction_type TEXT,
    prompt TEXT,
    response TEXT,
    model_used TEXT,
    tokens_used INT,
    latency_ms INT,
    thumbs_up BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS captures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    text TEXT NOT NULL,
    source TEXT CHECK (source IN ('pwa','telegram')),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL DEFAULT 'shivam',
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(date, checkin_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_behavioral_events_type ON behavioral_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_captures_processed ON captures(processed, created_at);
SQLEOF

echo "Tables created. Verifying..."
docker exec locus-postgres psql -U locus -d locus -c "\dt"

echo ""
echo "=== Step 2: Strip broken annotations from files ==="
# Files that got Groq annotations but failed on DB insert have ## ⟨locus⟩
# markers. We need to strip those so they get re-processed properly.
cd /opt/locus/backend
python3.11 << 'PYEOF'
from pathlib import Path
vault = Path("/vault")
files = list(vault.glob("00-Inbox/**/*.md")) + list(vault.glob("00-Inbox/**/*.txt"))
stripped = 0
for f in files:
    content = f.read_text(encoding="utf-8", errors="ignore")
    if "## ⟨locus⟩" in content:
        clean = content[:content.index("---\n\n## ⟨locus⟩")] if "---\n\n## ⟨locus⟩" in content else content[:content.index("## ⟨locus⟩")]
        f.write_text(clean.rstrip() + "\n", encoding="utf-8")
        stripped += 1
print(f"Stripped annotations from {stripped} files (will re-enrich properly)")
PYEOF

echo ""
echo "=== Step 3: Deploy enricher with rate-limit handling ==="
cat > /opt/locus/backend/services/vault_enricher.py << 'PYEOF'
import os, asyncio, httpx, asyncpg, json, time
from pathlib import Path
from datetime import datetime

GROQ_KEY = os.getenv("GROQ_API_KEY")
VAULT_PATH = "/vault"

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

async def call_groq_70b(content, retry=0):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "system", "content": ENRICHMENT_PROMPT},
                                {"role": "user", "content": content[:4000]}],
                  "temperature": 0.1, "response_format": {"type": "json_object"}}
        )
        if r.status_code == 429 and retry < 3:
            wait = 30 * (retry + 1)
            print(f"  Rate limited, waiting {wait}s...")
            await asyncio.sleep(wait)
            return await call_groq_70b(content, retry + 1)
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

    # Write to DB first, then annotate file (so partial failures don't leave broken state)
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
                print(f"  -> Task: {t.get('action','')[:60]}")
        elif cls == 'project' and e.get('project_if_applicable'):
            p = e['project_if_applicable']
            if isinstance(p, dict) and p.get('title'):
                await conn.execute("""INSERT INTO projects (user_id,title,description,faction,status)
                    VALUES ('shivam',$1,$2,$3,'active') ON CONFLICT DO NOTHING""",
                    p.get('title',file_path.stem)[:200], content[:500], faction)
                print(f"  -> Project: {p.get('title','')[:60]}")
        await conn.execute("INSERT INTO behavioral_events (user_id,event_type,data) VALUES ('shivam','vault_enrich',$1)",
            json.dumps({"file":file_path.name,"classification":cls,"faction":e.get('faction')})[:500])
    finally:
        await conn.close()

    # Only annotate file after DB write succeeds
    file_path.write_text(content + annotation, encoding="utf-8")
    return True

async def run_enrichment():
    vault = Path(VAULT_PATH)
    files = list(vault.glob("00-Inbox/**/*.md")) + list(vault.glob("00-Inbox/**/*.txt"))
    print(f"Vault enricher: {len(files)} files")
    enriched = 0
    errors = 0
    for i, f in enumerate(files):
        try:
            if await enrich_file(f):
                enriched += 1
                print(f"  [{enriched}/{len(files)}] done")
            await asyncio.sleep(5)  # 5 sec between files — Groq free tier safe
        except Exception as ex:
            print(f"  ERROR on {f.name}: {ex}")
            errors += 1
            await asyncio.sleep(10)  # Back off more on errors
    print(f"Done: {enriched}/{len(files)} enriched, {errors} errors")

if __name__ == "__main__":
    asyncio.run(run_enrichment())
PYEOF

echo "  Enricher v2 deployed (with retry + 5s delay)."

echo ""
echo "=== Step 4: Run enrichment (5s per file, ~5 min for 55 files) ==="
export GROQ_API_KEY=$(grep '^GROQ_API_KEY=' /opt/locus/.env | cut -d= -f2)
python3.11 /opt/locus/backend/services/vault_enricher.py

echo ""
echo "=== COMPLETE ==="
echo "Verify in DB:"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as enriched_events FROM behavioral_events WHERE event_type='vault_enrich';"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as tasks FROM tasks;"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as projects FROM projects;"
