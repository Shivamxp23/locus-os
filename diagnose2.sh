#!/bin/bash
echo "=== Check DB tables ==="
docker exec locus-postgres psql -U locus -d locus -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"

echo ""
echo "=== Check init.sql exists ==="
docker exec locus-postgres ls -la /docker-entrypoint-initdb.d/ 2>/dev/null || echo "no init dir"

echo ""
echo "=== Check enricher content ==="
head -30 /opt/locus/backend/services/vault_enricher.py

echo ""
echo "=== Check DB password in .env ==="
grep '^POSTGRES_PASSWORD=' /opt/locus/.env

echo ""
echo "=== Test DB connection directly ==="
docker exec locus-postgres psql -U locus -d locus -c "SELECT 1 as test;"
