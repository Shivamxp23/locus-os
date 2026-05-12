"""
diagnose_databases.py — Locus OS Database Health Report

Run on the VM (where Docker containers are running):
  python3 scripts/diagnose_databases.py

Or from within Docker network:
  docker exec locus-api python scripts/diagnose_databases.py
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime


# ── Config (reads from env or uses Docker-internal defaults) ──
PG_URL = os.getenv("DATABASE_URL", "postgresql://locus:PostgreSQL3301Locus@127.0.0.1:5432/locus")
NEO4J_URI = os.getenv("NEO4J_URL", "bolt://127.0.0.1:7687")
NEO4J_USER = "neo4j"
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "Neo4j3301Locus")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
VAULT_DIRS = ["/vault", "./vault", "../vault", os.path.expanduser("~/vault")]
REDIS_URL = os.getenv("REDIS_URL", "redis://:Redis3301Locus@127.0.0.1:6379/0")


def banner(title: str):
    width = 60
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")


async def check_postgres():
    banner("POSTGRESQL")
    try:
        import asyncpg
        conn = await asyncpg.connect(PG_URL)

        # List all tables with row counts
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
        )
        if not tables:
            print("  ⚠️  No tables found in public schema!")
            await conn.close()
            return

        total_rows = 0
        print(f"  Found {len(tables)} tables:\n")
        print(f"  {'Table':<35} {'Rows':>10}")
        print(f"  {'─' * 35} {'─' * 10}")

        for t in tables:
            tname = t['tablename']
            try:
                count = await conn.fetchval(f'SELECT count(*) FROM "{tname}";')
            except Exception:
                count = "ERROR"
            if isinstance(count, int):
                total_rows += count
            print(f"  {tname:<35} {count:>10}")

        print(f"\n  Total rows across all tables: {total_rows}")

        # Quick data quality checks
        print(f"\n  ── Data Quality ──")

        # Check daily_logs recency
        try:
            latest = await conn.fetchval("SELECT MAX(date) FROM daily_logs;")
            count_7d = await conn.fetchval(
                "SELECT count(*) FROM daily_logs WHERE date >= NOW() - INTERVAL '7 days';"
            )
            print(f"  Latest daily_log date: {latest}")
            print(f"  Daily logs in last 7 days: {count_7d}")
        except Exception as e:
            print(f"  daily_logs check failed: {e}")

        # Check tasks
        try:
            pending = await conn.fetchval("SELECT count(*) FROM tasks WHERE status = 'pending';")
            deferred = await conn.fetchval("SELECT count(*) FROM tasks WHERE deferral_count >= 2;")
            print(f"  Pending tasks: {pending}")
            print(f"  Tasks deferred 2+ times: {deferred}")
        except Exception as e:
            print(f"  tasks check failed: {e}")

        # Check ai_interactions
        try:
            ai_count = await conn.fetchval("SELECT count(*) FROM ai_interactions;")
            print(f"  AI interactions logged: {ai_count}")
        except Exception as e:
            print(f"  ai_interactions check failed: {e}")

        # Check if new v3 tables exist
        v3_tables = ['detected_patterns', 'user_identity', 'state_snapshots', 'daily_synthesis', 'reward_signals']
        existing_v3 = []
        for vt in v3_tables:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=$1);", vt
            )
            if exists:
                existing_v3.append(vt)
        print(f"\n  V3 tables present: {existing_v3 if existing_v3 else 'NONE — run migrate_v3_inference.sql'}")

        await conn.close()
        print("\n  ✅ PostgreSQL: CONNECTED")
    except ImportError:
        print("  ❌ asyncpg not installed")
    except Exception as e:
        print(f"  ❌ PostgreSQL: FAILED — {e}")


def check_neo4j():
    banner("NEO4J")
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

        with driver.session() as session:
            # Node counts by label
            nodes = session.run(
                "MATCH (n) RETURN labels(n) AS labels, count(n) AS count ORDER BY count DESC"
            ).data()

            if not nodes:
                print("  ⚠️  Graph is EMPTY — no nodes found!")
            else:
                print(f"  Nodes by label:\n")
                print(f"  {'Label':<35} {'Count':>10}")
                print(f"  {'─' * 35} {'─' * 10}")
                total_nodes = 0
                for n in nodes:
                    label_str = ", ".join(n['labels']) if n['labels'] else "(unlabeled)"
                    print(f"  {label_str:<35} {n['count']:>10}")
                    total_nodes += n['count']
                print(f"\n  Total nodes: {total_nodes}")

            # Edge counts by type
            edges = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
            ).data()

            if not edges:
                print("\n  ⚠️  No edges (relationships) found!")
            else:
                print(f"\n  Edges by type:\n")
                print(f"  {'Relationship':<35} {'Count':>10}")
                print(f"  {'─' * 35} {'─' * 10}")
                total_edges = 0
                for e in edges:
                    print(f"  {e['type']:<35} {e['count']:>10}")
                    total_edges += e['count']
                print(f"\n  Total edges: {total_edges}")

            # Check for Shivam node specifically
            shivam = session.run(
                "MATCH (p:Person {name:'Shivam'})-[r]->(n) "
                "RETURN type(r) AS rel, count(n) AS count ORDER BY count DESC LIMIT 10"
            ).data()
            if shivam:
                print(f"\n  Shivam's connections:")
                for s in shivam:
                    print(f"    -{s['rel']}-> {s['count']} nodes")
            else:
                print(f"\n  ⚠️  No Person node named 'Shivam' found!")

            # Check for edge weights (Hebbian)
            weighted = session.run(
                "MATCH ()-[r]->() WHERE r.weight IS NOT NULL RETURN count(r) AS count"
            ).data()
            w_count = weighted[0]['count'] if weighted else 0
            print(f"\n  Edges with weight property: {w_count}")

        driver.close()
        print("\n  ✅ Neo4j: CONNECTED")
    except ImportError:
        print("  ❌ neo4j driver not installed")
    except Exception as e:
        print(f"  ❌ Neo4j: FAILED — {e}")


async def check_qdrant():
    banner("QDRANT")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(f"{QDRANT_URL}/collections")
            if res.status_code != 200:
                print(f"  ❌ Qdrant returned HTTP {res.status_code}")
                return

            colls = res.json().get('result', {}).get('collections', [])
            if not colls:
                print("  ⚠️  No collections found!")
            else:
                print(f"  Found {len(colls)} collection(s):\n")
                print(f"  {'Collection':<30} {'Vectors':>10} {'Status':<15}")
                print(f"  {'─' * 30} {'─' * 10} {'─' * 15}")

                for c in colls:
                    cname = c['name']
                    info_res = await client.get(f"{QDRANT_URL}/collections/{cname}")
                    if info_res.status_code == 200:
                        info = info_res.json().get('result', {})
                        vec_count = info.get('vectors_count', info.get('points_count', 0))
                        status = info.get('status', 'unknown')
                        dim = info.get('config', {}).get('params', {}).get('vectors', {}).get('size', '?')
                        print(f"  {cname:<30} {vec_count:>10} {status:<15} (dim={dim})")
                    else:
                        print(f"  {cname:<30} {'ERROR':>10}")

        print("\n  ✅ Qdrant: CONNECTED")
    except ImportError:
        print("  ❌ httpx not installed")
    except Exception as e:
        print(f"  ❌ Qdrant: FAILED — {e}")


async def check_redis():
    banner("REDIS")
    try:
        import redis as redis_lib
        # Parse URL
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        info = r.info()
        keys = r.dbsize()
        memory = info.get('used_memory_human', '?')

        print(f"  Connected: {info.get('redis_version', '?')}")
        print(f"  Keys in DB: {keys}")
        print(f"  Memory used: {memory}")

        # Check for CURRENT_STATE
        state = r.get("locus:current_state")
        print(f"  CURRENT_STATE cached: {'YES' if state else 'NO'}")

        # Check for token usage tracking
        tokens = r.get("groq_tokens_today")
        print(f"  Groq tokens today: {tokens or 'not tracked'}")

        print("\n  ✅ Redis: CONNECTED")
    except ImportError:
        print("  ❌ redis not installed")
    except Exception as e:
        print(f"  ❌ Redis: FAILED — {e}")


def check_vault():
    banner("OBSIDIAN VAULT")
    vpath = None
    for d in VAULT_DIRS:
        p = Path(d)
        if p.exists() and p.is_dir():
            vpath = p
            break

    if not vpath:
        print(f"  ⚠️  Vault directory not found. Tried: {VAULT_DIRS}")
        return

    print(f"  Path: {vpath.resolve()}")

    md_files = list(vpath.rglob("*.md"))
    if not md_files:
        print("  ⚠️  No markdown files found!")
        return

    total_size = sum(f.stat().st_size for f in md_files)
    avg_size = total_size / len(md_files)
    largest = max(md_files, key=lambda f: f.stat().st_size)
    smallest_nonzero = [f for f in md_files if f.stat().st_size > 0]

    # Check for backlinks
    backlink_count = 0
    sample = md_files[:200]
    for f in sample:
        try:
            content = f.read_text(errors="ignore")
            if "[[" in content and "]]" in content:
                backlink_count += 1
        except Exception:
            pass

    # Check for frontmatter (YAML)
    frontmatter_count = 0
    for f in sample:
        try:
            content = f.read_text(errors="ignore")
            if content.strip().startswith("---"):
                frontmatter_count += 1
        except Exception:
            pass

    # Directory structure
    subdirs = set()
    for f in md_files:
        rel = f.relative_to(vpath)
        if len(rel.parts) > 1:
            subdirs.add(rel.parts[0])

    print(f"\n  Total markdown files: {len(md_files)}")
    print(f"  Total size: {total_size / 1024 / 1024:.2f} MB")
    print(f"  Average file size: {avg_size:.0f} bytes ({avg_size/1024:.1f} KB)")
    print(f"  Largest file: {largest.name} ({largest.stat().st_size / 1024:.1f} KB)")
    print(f"  Top-level folders: {len(subdirs)}")
    if subdirs:
        for sd in sorted(subdirs)[:15]:
            count = len([f for f in md_files if f.relative_to(vpath).parts[0] == sd])
            print(f"    📁 {sd}/ ({count} files)")

    print(f"\n  Backlinks (sample of {len(sample)}): {backlink_count} files have [[wikilinks]]")
    print(f"  Frontmatter (sample of {len(sample)}): {frontmatter_count} files have YAML frontmatter")

    # Recent activity
    recent_files = sorted(md_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
    print(f"\n  Recently modified:")
    for rf in recent_files:
        mtime = datetime.fromtimestamp(rf.stat().st_mtime)
        print(f"    {rf.name} — {mtime.strftime('%Y-%m-%d %H:%M')}")

    print(f"\n  ✅ Vault: FOUND")


async def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         LOCUS OS — DATABASE HEALTH REPORT               ║")
    print(f"║         {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z'):^48} ║")
    print("╚══════════════════════════════════════════════════════════╝")

    await check_postgres()
    check_neo4j()
    await check_qdrant()
    await check_redis()
    check_vault()

    banner("SUMMARY")
    print("  Run this script on the VM to get live results.")
    print("  If Neo4j is empty, run: python3 scripts/neo4j_seed.py")
    print("  If v3 tables missing, run: docker exec -i locus-postgres psql -U locus -d locus < scripts/migrate_v3_inference.sql")
    print()


if __name__ == "__main__":
    asyncio.run(main())
