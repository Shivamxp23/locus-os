import asyncio
import asyncpg
import httpx
from neo4j import GraphDatabase
import os
from pathlib import Path

# Config
PG_URL = "postgresql://locus:PostgreSQLLocus3301@127.0.0.1:5432/locus"
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "Neo4jLocus3301"
QDRANT_URL = "http://127.0.0.1:6333"
VAULT_DIR = "/vault" # Assuming it might be /vault or ./vault

async def check_postgres():
    try:
        conn = await asyncpg.connect(PG_URL)
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public';")
        print("=== PostgreSQL ===")
        for t in tables:
            tname = t['tablename']
            count = await conn.fetchval(f"SELECT count(*) FROM {tname};")
            print(f"Table '{tname}': {count} rows")
        await conn.close()
    except Exception as e:
        print(f"Postgres Error: {e}")

def check_neo4j():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            print("\n=== Neo4j ===")
            nodes = session.run("MATCH (n) RETURN labels(n) AS label, count(n) AS count").data()
            print("Nodes:")
            for n in nodes:
                print(f"  {n['label']}: {n['count']}")
            edges = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count").data()
            print("Edges:")
            for e in edges:
                print(f"  {e['type']}: {e['count']}")
        driver.close()
    except Exception as e:
        print(f"Neo4j Error: {e}")

async def check_qdrant():
    print("\n=== Qdrant ===")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{QDRANT_URL}/collections")
            if res.status_code == 200:
                colls = res.json().get('result', {}).get('collections', [])
                if not colls:
                    print("No collections found.")
                for c in colls:
                    cname = c['name']
                    info = await client.get(f"{QDRANT_URL}/collections/{cname}")
                    if info.status_code == 200:
                        count = info.json().get('result', {}).get('vectors_count', 0)
                        print(f"Collection '{cname}': {count} vectors")
            else:
                print(f"Qdrant returned {res.status_code}")
    except Exception as e:
        print(f"Qdrant Error: {e}")

def check_vault():
    print("\n=== Obsidian Vault ===")
    # try /vault, if not exist, try ./vault, etc
    vpath = Path(VAULT_DIR)
    if not vpath.exists():
        vpath = Path("./vault")
    if not vpath.exists():
        vpath = Path("../vault")
    if not vpath.exists():
        print("Vault directory not found.")
        return

    md_files = list(vpath.rglob("*.md"))
    total_size = sum(f.stat().st_size for f in md_files)
    avg_size = total_size / len(md_files) if md_files else 0

    backlinks_exist = False
    for f in md_files[:100]: # check sample
        content = f.read_text(errors="ignore")
        if "[[" in content and "]]" in content:
            backlinks_exist = True
            break

    print(f"Total Markdown files: {len(md_files)}")
    print(f"Average file size: {avg_size:.2f} bytes")
    print(f"Backlinks exist: {backlinks_exist}")

async def main():
    print("Running diagnostic script...\n")
    await check_postgres()
    check_neo4j()
    await check_qdrant()
    check_vault()
    print("\nHealth report complete.")

if __name__ == "__main__":
    asyncio.run(main())
