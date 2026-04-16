#!/bin/bash
set -e

echo "=== Step 1: Strip broken annotations ==="
python3.11 - <<'PYEOF'
from pathlib import Path
vault = Path("/vault")
files = list(vault.glob("00-Inbox/**/*.md")) + list(vault.glob("00-Inbox/**/*.txt"))
stripped = 0
for f in files:
    content = f.read_text(encoding="utf-8", errors="ignore")
    if "locus" in content and ("## " in content):
        idx = content.find("---\n\n## ")
        if idx > 0 and "locus" in content[idx:idx+50]:
            clean = content[:idx].rstrip() + "\n"
            f.write_text(clean, encoding="utf-8")
            stripped += 1
            print(f"  Stripped: {f.name}")
print(f"Stripped {stripped} files")
PYEOF

echo ""
echo "=== Step 2: Fix init.sql (remove directory, create file) ==="
rm -rf /opt/locus/scripts/init.sql
cp /tmp/create_tables.sql /opt/locus/scripts/init.sql
ls -la /opt/locus/scripts/init.sql

echo ""
echo "=== Step 3: Verify enricher is deployed ==="
head -5 /opt/locus/backend/services/vault_enricher.py
echo "..."
wc -l /opt/locus/backend/services/vault_enricher.py

echo ""
echo "=== Step 4: Run enrichment ==="
cd /opt/locus/backend
export GROQ_API_KEY=$(grep '^GROQ_API_KEY=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_PASSWORD=$(grep '^POSTGRES_PASSWORD=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_USER=$(grep '^POSTGRES_USER=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_DB=$(grep '^POSTGRES_DB=' /opt/locus/.env | cut -d= -f2)
python3.11 services/vault_enricher.py

echo ""
echo "=== Verification ==="
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as enriched_events FROM behavioral_events WHERE event_type='vault_enrich';"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as total_tasks FROM tasks;"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as total_projects FROM projects;"
