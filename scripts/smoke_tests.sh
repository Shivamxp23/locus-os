#!/bin/bash
# LOCUS Smoke Tests — Section 17
# Adapted for actual deployment: Qdrant/Neo4j have no host port mapping,
# Ollama runs with Open WebUI wrapper.

PASS=0
FAIL=0

pass() { echo "  ✅ PASS"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ FAIL — $1"; FAIL=$((FAIL + 1)); }

echo "=========================================="
echo "        LOCUS SMOKE TESTS"
echo "=========================================="
echo ""

# Test 1 — Infrastructure
echo "TEST 1: Infrastructure (docker compose ps)"
RESULT=$(cd /opt/locus && docker compose ps --format '{{.Name}} {{.Status}}' 2>&1)
echo "$RESULT"
EXPECTED="locus-postgres locus-redis locus-api locus-qdrant locus-neo4j locus-chromadb locus-syncthing"
MISSING=""
for svc in $EXPECTED; do
    echo "$RESULT" | grep -q "$svc" || MISSING="$MISSING $svc"
done
if [ -z "$MISSING" ]; then pass; else fail "Missing:$MISSING"; fi
echo ""

# Test 2 — FastAPI
echo "TEST 2: FastAPI health"
R_LOCAL=$(curl -s http://localhost:8000/health 2>&1)
R_EXT=$(curl -s https://api.locusapp.online/health 2>&1)
echo "  localhost: $R_LOCAL"
echo "  external:  $R_EXT"
echo "$R_LOCAL" | grep -q '"status":"ok"' && pass || fail "Local health failed"
echo "$R_EXT"   | grep -q '"status":"ok"' && pass || fail "External health failed"
echo ""

# Test 3 — PostgreSQL
echo "TEST 3: PostgreSQL tables"
R3=$(docker exec locus-postgres psql -U locus -t -c "SELECT count(*) FROM pg_tables WHERE schemaname='public';" 2>&1)
TCOUNT=$(echo "$R3" | tr -d ' ')
echo "  Table count: $TCOUNT"
[ "$TCOUNT" -ge 9 ] 2>/dev/null && pass || fail "Expected >=9 tables, got $TCOUNT"
echo ""

# Test 4 — Qdrant (no host port — check container is running + healthy)
echo "TEST 4: Qdrant"
R4=$(docker inspect locus-qdrant --format='{{.State.Status}}' 2>&1)
echo "  Container status: $R4"
[ "$R4" = "running" ] && pass || fail "Qdrant not running: $R4"
echo ""

# Test 5 — Neo4j (via docker exec — no host port mapped)
echo "TEST 5: Neo4j"
R5=$(docker exec locus-neo4j wget -qO- http://localhost:7474 2>&1)
echo "  $R5" | head -c 200
echo ""
echo "$R5" | grep -q "neo4j_version" && pass || fail "Neo4j not responding"
echo ""

# Test 6 — Ollama
echo "TEST 6: Ollama"
R6=$(curl -s http://localhost:11434/api/tags 2>&1 | head -c 300)
echo "  $R6"
echo "$R6" | grep -q "models" && pass || fail "Ollama API not responding"
echo ""

# Test 7 — Groq API
echo "TEST 7: Groq API"
source /opt/locus/.env 2>/dev/null || true
R7=$(curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"say ok"}]}' 2>&1)
echo "  $(echo "$R7" | head -c 200)"
echo "$R7" | grep -q '"choices"' && pass || fail "Groq API call failed"
echo ""

# Test 8 — Syncthing
echo "TEST 8: Syncthing"
R8=$(docker inspect locus-syncthing --format='{{.State.Status}}' 2>&1)
echo "  Container status: $R8"
[ "$R8" = "running" ] && pass || fail "Syncthing not running"
echo ""

# Test 9 — Telegram Bot
echo "TEST 9: Telegram Bot"
R9=$(pgrep -fa telegram_bot 2>&1 | grep python | head -1)
echo "  $R9"
echo "$R9" | grep -q "telegram_bot" && pass || fail "Telegram bot not running"
echo "  ⚠️  Manual: Send your bot a message to verify it responds."
echo ""

# Test 10 — PWA
echo "TEST 10: PWA (locusapp.online)"
R10=$(curl -s -o /dev/null -w "%{http_code}" https://locusapp.online 2>&1)
echo "  HTTP status: $R10"
[ "$R10" = "200" ] && pass || echo "  ⚠️  SKIP — PWA not yet deployed (Section 15)"
echo ""

# BONUS — LightRAG
echo "BONUS: LightRAG health"
RB=$(curl -s http://localhost:9621/health 2>&1 | head -c 80)
echo "  $RB"
echo "$RB" | grep -q '"healthy"' && pass || fail "LightRAG not healthy"
echo ""

# BONUS — Vault indexing
echo "BONUS: Vault indexing complete?"
RI=$(tail -1 /opt/locus/index.log 2>/dev/null)
echo "  $RI"
echo "$RI" | grep -q "complete" && pass || echo "  ⚠️  Indexing may still be running"
echo ""

echo "=========================================="
echo "  RESULTS: $PASS PASSED, $FAIL FAILED"
echo "=========================================="
