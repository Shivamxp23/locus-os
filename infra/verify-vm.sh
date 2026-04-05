#!/bin/bash
set -e

echo "=== VERIFICATION 1: File Inventory ==="
echo "--- Locus Skill ---"
ls -la /opt/locus-os/openclaw/skills/locus/
ls -la /opt/locus-os/openclaw/skills/locus/handlers/
echo ""
echo "--- Modifications ---"
ls -la /opt/locus-os/openclaw/src/config/locus-* 2>/dev/null || echo "  No config files"
ls -la /opt/locus-os/openclaw/src/plugins/locus-* 2>/dev/null || echo "  No plugin files"
echo ""
echo "--- Backend ---"
ls -la /opt/locus-os/backend/app/main.py /opt/locus-os/backend/requirements.txt /opt/locus-os/backend/Dockerfile
echo ""
echo "--- Infrastructure ---"
ls -la /opt/locus-os/infra/docker-compose.yml
echo ""
echo "--- .env ---"
ls -la /opt/locus-os/.env
echo ""

echo "=== VERIFICATION 2: LOCUS MODIFICATION Markers ==="
grep -rn "LOCUS MODIFICATION" /opt/locus-os/openclaw/src/ --include="*.ts" | grep -v ".test." | head -20
echo ""

echo "=== VERIFICATION 3: .env required vars ==="
for var in TELEGRAM_TOKEN TELEGRAM_OWNER_ID LOCUS_API_URL LOCUS_SERVICE_TOKEN GEMINI_API_KEY GROQ_API_KEY SECRET_KEY POSTGRES_PASSWORD; do
  val=$(grep "^${var}=" /opt/locus-os/.env | head -1 | cut -d= -f2 | cut -c1-10)
  if [ -n "$val" ]; then
    echo "  OK: ${var} = ${val}..."
  else
    echo "  MISSING: ${var}"
  fi
done
echo ""

echo "=== VERIFICATION 4: Python check ==="
python3 --version 2>/dev/null || echo "Python3 not found"
pip3 --version 2>/dev/null || echo "pip3 not found"
echo ""

echo "=== VERIFICATION 5: Docker check ==="
docker --version
docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo "docker compose not found"
echo ""

echo "=== VERIFICATION 6: FastAPI import test ==="
cd /opt/locus-os/backend
pip3 install -q fastapi pydantic uvicorn 2>/dev/null
python3 -c "from app.main import app; routes=[r for r in app.routes if hasattr(r,'methods')]; print(f'FastAPI OK: {len(routes)} routes'); [print(f'  {list(r.methods)} {r.path}') for r in routes]" 2>&1
echo ""

echo "=== VERIFICATION 7: Docker Compose YAML valid ==="
python3 -c "import yaml; data=yaml.safe_load(open('/opt/locus-os/infra/docker-compose.yml')); print(f'Valid YAML. Services: {list(data[\"services\"].keys())}')" 2>&1 || \
python3 -c "
import json
with open('/opt/locus-os/infra/docker-compose.yml') as f:
    content = f.read()
print('YAML file readable, contains', len(content), 'bytes')
print('Services mentioned:', [l.strip().rstrip(':') for l in content.split('\n') if l.strip().endswith(':') and not l.startswith(' ') and not l.startswith('#') and 'services' not in l and 'volumes' not in l and 'networks' not in l])
"
echo ""

echo "=== ALL VERIFICATIONS COMPLETE ==="
