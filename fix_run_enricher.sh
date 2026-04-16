#!/bin/bash
set -e

echo "=== Check current enricher default password ==="
grep 'DB_PASS' /opt/locus/backend/services/vault_enricher.py

echo ""
echo "=== Fix: Update enricher default password to match .env ==="
# The enricher script from the earlier deploy has wrong default password
# Let's just patch the default
sed -i "s/PostgreSQLLocus3301/PostgreSQL@3301.Locus/g" /opt/locus/backend/services/vault_enricher.py

echo "After fix:"
grep 'DB_PASS' /opt/locus/backend/services/vault_enricher.py

echo ""
echo "=== Now run enricher with explicit env + stderr visible ==="
cd /opt/locus/backend
export GROQ_API_KEY=$(grep '^GROQ_API_KEY=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_PASSWORD=$(grep '^POSTGRES_PASSWORD=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_USER=$(grep '^POSTGRES_USER=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_DB=$(grep '^POSTGRES_DB=' /opt/locus/.env | cut -d= -f2)

echo "Starting enrichment with password: $POSTGRES_PASSWORD"
echo ""
python3.11 -u services/vault_enricher.py 2>&1
