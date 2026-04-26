"""
neo4j_seed.py — Initialize Shivam's personality graph.
Run ONCE after first docker compose up.

Usage on VM:
  cd /opt/locus
  export $(grep -v '^#' .env | xargs)
  python3 scripts/neo4j_seed.py
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
                p.role = 'CS undergraduate & aspiring cinematographer building Locus OS',
                p.location = 'Vadodara, Gujarat, India',
                p.seeded = datetime()
        """)

        print("Seeding interests...")
        interests = [
            "filmmaking", "cinematography", "computer science",
            "personal knowledge management", "self-optimization",
            "philosophy", "productivity systems", "AI", "PKM",
            "obsidian", "note-taking", "systems thinking",
            "stoicism", "startups", "writing",
        ]
        for name in interests:
            await s.run("""
                MERGE (i:Interest {name: $name})
                SET i.last_mentioned = datetime()
                WITH i MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:INTERESTED_IN]->(i)
            """, name=name)

        print("Seeding active projects...")
        projects = [
            {"name": "Locus OS",      "desc": "Personal Cognitive Operating System — solo build"},
            {"name": "Cinematography","desc": "Learning and practising filmmaking"},
        ]
        for proj in projects:
            await s.run("""
                MERGE (pr:Project {name: $name})
                ON CREATE SET pr.status = 'active',
                              pr.description = $desc,
                              pr.first_seen = datetime()
                SET pr.last_mentioned = datetime()
                WITH pr MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:WORKING_ON]->(pr)
            """, name=proj["name"], desc=proj["desc"])

        print("Seeding personality traits...")
        traits = [
            ("systematic",        0.9),
            ("philosophical",     0.8),
            ("perfectionist",     0.8),
            ("avoidance-prone",   0.7),
            ("deep-work capable", 0.8),
            ("self-aware",        0.85),
        ]
        for name, confidence in traits:
            await s.run("""
                MERGE (t:Trait {name: $name})
                ON CREATE SET t.confidence = $conf, t.first_seen = datetime()
                ON MATCH SET  t.confidence = $conf
                WITH t MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[rel:HAS_TRAIT]->(t)
                ON CREATE SET rel.confidence = $conf
                ON MATCH SET  rel.confidence = $conf
            """, name=name, conf=confidence)

        print("Seeding known avoidance patterns...")
        avoidances = [
            ("cold outreach and sales conversations",  3),
            ("following up on Monevo-related tasks",   2),
            ("academic assignment deadlines",          2),
        ]
        for desc, freq in avoidances:
            await s.run("""
                MERGE (a:Avoidance {description: $desc})
                ON CREATE SET a.frequency = $freq, a.first_seen = datetime()
                ON MATCH SET  a.frequency = $freq
                WITH a MATCH (p:Person {name: 'Shivam'})
                MERGE (p)-[:AVOIDS]->(a)
            """, desc=desc, freq=freq)

        print("Creating schema constraints & indexes...")
        for stmt in [
            "CREATE CONSTRAINT person_name_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT interest_name_unique IF NOT EXISTS FOR (i:Interest) REQUIRE i.name IS UNIQUE",
            "CREATE CONSTRAINT avoidance_desc_unique IF NOT EXISTS FOR (a:Avoidance) REQUIRE a.description IS UNIQUE",
            "CREATE CONSTRAINT trait_name_unique IF NOT EXISTS FOR (t:Trait) REQUIRE t.name IS UNIQUE",
        ]:
            try:
                await s.run(stmt)
            except Exception as e:
                print(f"  Constraint note: {e}")

        for stmt in [
            "CREATE INDEX pattern_strength IF NOT EXISTS FOR (pat:Pattern) ON (pat.strength)",
            "CREATE INDEX interest_last_mentioned IF NOT EXISTS FOR (i:Interest) ON (i.last_mentioned)",
            "CREATE INDEX trait_confidence IF NOT EXISTS FOR (t:Trait) ON (t.confidence)",
        ]:
            try:
                await s.run(stmt)
            except Exception as e:
                print(f"  Index note: {e}")

        print("\nVerification:")
        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:INTERESTED_IN]->(i) RETURN count(i) AS cnt")
        rec = await r.single()
        print(f"  Interests: {rec['cnt']}")

        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:WORKING_ON]->(pr) RETURN count(pr) AS cnt")
        rec = await r.single()
        print(f"  Projects: {rec['cnt']}")

        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:HAS_TRAIT]->(t) RETURN count(t) AS cnt")
        rec = await r.single()
        print(f"  Traits: {rec['cnt']}")

        r = await s.run("MATCH (p:Person {name:'Shivam'})-[:AVOIDS]->(a) RETURN count(a) AS cnt")
        rec = await r.single()
        print(f"  Avoidances: {rec['cnt']}")

    await driver.close()
    print("\nSeed complete. Neo4j graph initialized.")
    print("The graph grows automatically as you converse with the bot.")


if __name__ == "__main__":
    asyncio.run(seed())
