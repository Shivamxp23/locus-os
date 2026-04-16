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
    if e.get('contradictions'):
        annotation += f"\n**Warning:** {e['contradictions']}\n"

    if e.get('task_if_applicable'):
        t = e['task_if_applicable']
        if isinstance(t, dict) and t.get('action'):
            annotation += f"\n**Task:** {t.get('action', '')} (Est: {t.get('estimated_hours', '?')}h, P{t.get('priority', '?')}/U{t.get('urgency', '?')})\n"

    # Write to DB first, then annotate file
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
    print(f"Vault enricher: {len(files)} files found")
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
    print(f"\n{'='*50}")
    print(f"DONE: {enriched}/{len(files)} enriched, {errors} errors")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(run_enrichment())
