#!/bin/bash
echo "=== Debug: Check env vars as enricher sees them ==="
cd /opt/locus/backend
export GROQ_API_KEY=$(grep '^GROQ_API_KEY=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_PASSWORD=$(grep '^POSTGRES_PASSWORD=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_USER=$(grep '^POSTGRES_USER=' /opt/locus/.env | cut -d= -f2)
export POSTGRES_DB=$(grep '^POSTGRES_DB=' /opt/locus/.env | cut -d= -f2)

echo "GROQ_API_KEY starts with: ${GROQ_API_KEY:0:10}"
echo "POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
echo "POSTGRES_USER: $POSTGRES_USER"
echo "POSTGRES_DB: $POSTGRES_DB"

echo ""
echo "=== Test: Can python connect to DB? ==="
python3.11 -c "
import asyncio, asyncpg, os

async def test():
    pw = os.getenv('POSTGRES_PASSWORD', 'NOTSET')
    print(f'Using password: {pw}')
    try:
        conn = await asyncpg.connect(host='127.0.0.1', port=5432, user='locus', password=pw, database='locus')
        tables = await conn.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
        print(f'Connected! Tables: {[t[\"tablename\"] for t in tables]}')
        await conn.close()
    except Exception as e:
        print(f'Connection FAILED: {e}')
        # Try with hardcoded password
        try:
            conn2 = await asyncpg.connect(host='127.0.0.1', port=5432, user='locus', password='PostgreSQLLocus3301', database='locus')
            tables = await conn2.fetch(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
            print(f'Hardcoded password worked! Tables: {[t[\"tablename\"] for t in tables]}')
            await conn2.close()
        except Exception as e2:
            print(f'Hardcoded password also failed: {e2}')

asyncio.run(test())
"

echo ""
echo "=== Test: Can python reach Groq? ==="
python3.11 -c "
import asyncio, httpx, os

async def test():
    key = os.getenv('GROQ_API_KEY', 'NOTSET')
    print(f'Using key: {key[:15]}...')
    async with httpx.AsyncClient(timeout=15) as c:
        try:
            r = await c.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {key}'})
            print(f'Groq API status: {r.status_code}')
            if r.status_code == 200:
                models = [m['id'] for m in r.json().get('data',[])]
                print(f'Available models: {[m for m in models if \"llama\" in m][:5]}')
        except Exception as e:
            print(f'Groq FAILED: {e}')

asyncio.run(test())
"

echo ""
echo "=== Test: Vault files exist? ==="
find /vault/00-Inbox -name '*.md' -o -name '*.txt' 2>/dev/null | head -5
echo "Total:"
find /vault/00-Inbox -name '*.md' -o -name '*.txt' 2>/dev/null | wc -l
