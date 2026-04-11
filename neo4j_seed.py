"""
neo4j_seed.py — Run ONCE to initialize Shivam's personality graph.

Seeds the graph with baseline known data so the bot has something to work
with from day one instead of starting completely empty.

Run on the VM:
  cd /opt/locus
  export $(grep -v '^#' .env | xargs)
  python3 neo4j_seed.py
"""

import asyncio, os

NEO4J_URL      = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


async def seed():
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))

    async with driver.session() as s:

        print("Creating Person node...")
        await s.run("""
            MERGE (p:Person {name: 'Shivam'})
            SET p.age = 23,
                p.role = 'CS undergraduate student & aspiring cinematographer',
                p.location = 'Vadodara, Gujarat, India',
                p.seeded = datetime()
        """)

        print("Creating interests...")
        interests = [
            "filmmaking", "cinematography", "computer science",
            "personal knowledge management", "self-optimization",
            "philosophy", "productivity systems", "AI", "PKM",
            "obsidian", "note-taking", "systems thinking"
        ]
        for interest in interests:
            await s.run("""
                MERGE (i:Interest {name: $name})
                SET i.last_mentioned = datetime()
                WITH i
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:INTERESTED_IN]->(i)
            """, name=interest)

        print("Creating active projects...")
        projects = [
            {"name": "Locus OS", "description": "Personal Cognitive Operating System — solo build"},
            {"name": "Cinematography", "description": "Learning and practising filmmaking"},
        ]
        for proj in projects:
            await s.run("""
                MERGE (pr:Project {name: $name})
                ON CREATE SET pr.status = 'active',
                              pr.description = $desc,
                              pr.first_seen = datetime()
                WITH pr
                MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:WORKING_ON]->(pr)
            """, name=proj["name"], desc=proj["description"])

        print("Creating schema constraints and indexes...")
        # Constraints
        for stmt in [
            "CREATE CONSTRAINT person_name_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT interest_name_unique IF NOT EXISTS FOR (i:Interest) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT avoidance_desc_unique IF NOT EXISTS FOR (a:Avoidance) REQUIRE a.description IS UNIQUE",
        ]:
            try:
                await s.run(stmt)
            except Exception as e:
                print(f"  Constraint note: {e}")

        # Indexes
        for stmt in [
            "CREATE INDEX pattern_strength IF NOT EXISTS FOR (pat:Pattern) ON (pat.strength)",
            "CREATE INDEX interest_last_mentioned IF NOT EXISTS FOR (i:Interest) ON (i.last_mentioned)",
        ]:
            try:
                await s.run(stmt)
            except Exception as e:
                print(f"  Index note: {e}")

        print("Verifying seed...")
        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:INTERESTED_IN]->(i) RETURN count(i) AS cnt")
        record = await r.single()
        print(f"  Interests seeded: {record['cnt']}")

        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:WORKING_ON]->(pr) RETURN count(pr) AS cnt")
        record = await r.single()
        print(f"  Projects seeded: {record['cnt']}")

    await driver.close()
    print("\nSeed complete. Neo4j personality graph initialized.")
    print("The graph will grow automatically as you use the bot.")


if __name__ == "__main__":
    asyncio.run(seed())
