#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Phase 1 Deploy Script — Replaces locus-api with new FastAPI stub
# Keeps existing postgres, redis, neo4j, qdrant, ollama, syncthing
# ═══════════════════════════════════════════════════════════════
set -e

echo "=== Phase 1 Deploy ==="
echo "Step 1: Stop old locus-api and locus-openclaw containers..."
docker stop locus-api locus-openclaw 2>/dev/null || true
docker rm locus-api locus-openclaw 2>/dev/null || true

echo ""
echo "Step 2: Build new locus-api image..."
cd /opt/locus-os
docker build -t locus-api:phase1 -f backend/Dockerfile backend/

echo ""
echo "Step 3: Get existing network name..."
NETWORK=$(docker inspect locus-postgres --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}')
echo "  Using network: $NETWORK"

echo ""
echo "Step 4: Start new locus-api on same network as existing postgres..."
docker run -d \
  --name locus-api \
  --network "$NETWORK" \
  --env-file /opt/locus-os/.env \
  -e PORT=3000 \
  -e POSTGRES_HOST=locus-postgres \
  -e REDIS_URL=redis://:$(grep '^REDIS_PASSWORD=' /opt/locus-os/.env | cut -d= -f2)@locus-redis:6379/0 \
  -p 3000:3000 \
  --restart unless-stopped \
  locus-api:phase1

echo ""
echo "Step 5: Wait 10s for startup..."
sleep 10

echo ""
echo "Step 6: Health check..."
HEALTH=$(curl -s http://localhost:3000/health 2>&1)
echo "  Response: $HEALTH"

echo ""
echo "Step 7: Test audit endpoint..."
AUDIT=$(curl -s -X POST http://localhost:3000/api/v1/internal/audit/openclaw \
  -H "Content-Type: application/json" \
  -d '{"event_type":"test","tool_name":"deploy_test","timestamp":"2026-04-05T18:00:00Z","response_status":"ok","duration_ms":42}')
echo "  Audit response: $AUDIT"

echo ""
echo "Step 8: Test morning log endpoint..."
MORNING=$(curl -s -X POST http://localhost:3000/api/v1/log/morning \
  -H "Content-Type: application/json" \
  -d '{"energy":8,"mood":7,"sleep":7,"stress":3,"time_available":6.0}')
echo "  Morning log response: $MORNING"

echo ""
echo "Step 9: Test Appledore search endpoint..."
APPLEDORE=$(curl -s -X POST http://localhost:3000/api/v1/appledore/search \
  -H "Content-Type: application/json" \
  -d '{"query":"phase 1 hardening"}')
echo "  Appledore response: $APPLEDORE"

echo ""
echo "Step 10: Container status..."
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E "locus|NAMES"

echo ""
echo "Step 11: API Logs..."
docker logs locus-api --tail 15

echo ""
echo "=== PHASE 1 DEPLOY COMPLETE ==="
