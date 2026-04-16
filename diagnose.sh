#!/bin/bash
echo "=== Docker Status ==="
docker compose -f /opt/locus/docker-compose.yml ps 2>/dev/null || echo "docker compose failed"

echo ""
echo "=== Enricher file ==="
ls -la /opt/locus/backend/services/vault_enricher.py 2>/dev/null || echo "enricher NOT found at expected path"

echo ""
echo "=== Vault file count ==="
find /vault/00-Inbox -name '*.md' -o -name '*.txt' 2>/dev/null | wc -l

echo ""
echo "=== Already enriched files ==="
grep -rl 'locus' /vault/00-Inbox/ 2>/dev/null | wc -l

echo ""
echo "=== DB check ==="
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as enriched FROM behavioral_events WHERE event_type='vault_enrich';" 2>/dev/null || echo "behavioral_events query failed"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as tasks FROM tasks;" 2>/dev/null || echo "tasks query failed"
docker exec locus-postgres psql -U locus -d locus -c "SELECT count(*) as projects FROM projects;" 2>/dev/null || echo "projects query failed"
docker exec locus-postgres psql -U locus -d locus -c "\dt" 2>/dev/null || echo "table list failed"

echo ""
echo "=== Python version ==="
python3.11 --version 2>/dev/null || echo "python3.11 not found"
python3 --version 2>/dev/null || echo "python3 not found"

echo ""
echo "=== pip packages ==="
python3.11 -m pip list 2>/dev/null | grep -iE 'asyncpg|httpx' || echo "packages not found via python3.11"

echo ""
echo "=== Postgres port mapping ==="
docker port locus-postgres 2>/dev/null || echo "no port mappings"

echo ""
echo "=== GROQ key set? ==="
grep '^GROQ_API_KEY=' /opt/locus/.env | head -c 20
echo "..."

echo ""
echo "=== Last enricher log ==="
tail -30 /var/log/vault_enricher.log 2>/dev/null || echo "no enricher log found"

echo ""
echo "=== Sample unenriched file ==="
find /vault/00-Inbox -name '*.md' -exec grep -L 'locus' {} \; 2>/dev/null | head -5 || echo "all files enriched or none found"
