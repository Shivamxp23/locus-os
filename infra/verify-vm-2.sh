#!/bin/bash
echo "=== VERIFICATION 6: FastAPI import test ==="
cd /opt/locus-os/backend
pip3 install -q fastapi pydantic uvicorn 2>/dev/null
python3 -c "
from app.main import app
routes = [r for r in app.routes if hasattr(r, 'methods')]
print(f'FastAPI OK: {len(routes)} routes')
for r in routes:
    print(f'  {list(r.methods)} {r.path}')
"
echo ""

echo "=== VERIFICATION 7: Docker Compose YAML ==="
python3 -c "
import yaml
data = yaml.safe_load(open('/opt/locus-os/infra/docker-compose.yml'))
print(f'Valid YAML. Services: {list(data[\"services\"].keys())}')
"
echo ""

echo "=== VERIFICATION 8: Docker Build — FastAPI Backend ==="
cd /opt/locus-os
docker build -t locus-api:test -f backend/Dockerfile backend/ 2>&1
echo "Docker build exit code: $?"

echo ""
echo "=== VERIFICATION 9: Docker Compose Config ==="
cd /opt/locus-os/infra
docker compose --env-file /opt/locus-os/.env config --services 2>&1
echo ""

echo "=== VERIFICATION 10: Start locus-api container ==="
cd /opt/locus-os/infra
docker compose --env-file /opt/locus-os/.env up -d locus-postgres locus-api 2>&1
echo "Waiting 15s for startup..."
sleep 15

echo "=== VERIFICATION 11: Health Check ==="
curl -s http://localhost:3000/health 2>&1
echo ""

echo "=== VERIFICATION 12: Container Status ==="
docker compose --env-file /opt/locus-os/.env ps 2>&1
echo ""

echo "=== VERIFICATION 13: API Logs ==="
docker compose --env-file /opt/locus-os/.env logs locus-api --tail 20 2>&1
echo ""

echo "=== ALL VM VERIFICATIONS COMPLETE ==="
