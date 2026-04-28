import os
import logging
from typing import Optional
import asyncpg
from backend.services.qdrant_service import direct_search

log = logging.getLogger("brain.retriever")
DATABASE_URL = os.getenv("DATABASE_URL")
NEO4J_URL = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def classify_query(query: str) -> str:
    q = query.lower()
    
    postgres_keywords = ["task", "did i", "this week", "score", "dcs", "log", "check-in", "overdue", "today"]
    if any(kw in q for kw in postgres_keywords):
        return "postgres"
        
    graph_keywords = ["pattern", "connected", "related", "skill", "relationship", "model", "trait"]
    if any(kw in q for kw in graph_keywords):
        return "graph"
        
    return "qdrant"

async def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    results = await direct_search(query, limit=top_k)
    # Convert qdrant format to our format
    formatted = []
    for r in results:
        payload = r.get("payload", {})
        formatted.append({
            "text": payload.get("text", payload.get("chunk_text", "")),
            "source": payload.get("source_file", payload.get("file_path", "unknown")),
            "score": r.get("score", 0.0)
        })
    return formatted

async def structured_query(intent: str, params: dict = None) -> list[dict]:
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        results = []
        try:
            if intent == "recent_tasks":
                rows = await conn.fetch("SELECT title, status, estimated_hours FROM tasks WHERE status != 'done' ORDER BY created_at DESC LIMIT 10")
            elif intent == "checkin_history":
                rows = await conn.fetch("SELECT date, checkin_type, dcs, mode FROM daily_logs ORDER BY date DESC LIMIT 10")
            elif intent == "deferred_tasks":
                rows = await conn.fetch("SELECT title, deferral_count FROM tasks WHERE deferral_count >= 1 ORDER BY deferral_count DESC LIMIT 10")
            elif intent == "faction_scores":
                rows = await conn.fetch("SELECT faction, actual_hours, target_hours FROM faction_stats ORDER BY week_start DESC LIMIT 4")
            else:
                # Default query if intent not perfectly matched
                rows = await conn.fetch("SELECT title, status FROM tasks WHERE status = 'pending' LIMIT 5")
                
            for r in rows:
                text_repr = ", ".join([f"{k}: {v}" for k, v in dict(r).items()])
                results.append({"text": text_repr, "source": "postgres", "score": 1.0})
        finally:
            await conn.close()
        return results
    except Exception as e:
        log.error(f"Structured query failed: {e}")
        return []

async def graph_query(entity: str = "", relationship: str = None) -> list[dict]:
    results = []
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))
        
        async with driver.session() as s:
            # We'll pull recent traits, patterns and projects since the query wants patterns or relationships
            q = """
            MATCH (p:Person {name:'Shivam'})-[r]->(node)
            RETURN type(r) as rel, labels(node)[0] as type, node.name as name, node.description as desc
            LIMIT 20
            """
            rows = await s.run(q)
            async for r in rows:
                val = r["name"] or r["desc"]
                text_repr = f"User has relationship {r['rel']} with {r['type']}: {val}"
                results.append({"text": text_repr, "source": "neo4j", "score": 1.0})
                
        await driver.close()
    except Exception as e:
        log.error(f"Graph query failed: {e}")
    return results

async def retrieve(query: str) -> dict:
    mode = classify_query(query)
    results = []
    
    if mode == "postgres":
        intent = "recent_tasks"
        if "dcs" in query.lower() or "check-in" in query.lower():
            intent = "checkin_history"
        elif "overdue" in query.lower() or "avoid" in query.lower():
            intent = "deferred_tasks"
        elif "score" in query.lower():
            intent = "faction_scores"
        results = await structured_query(intent)
        
    elif mode == "graph":
        results = await graph_query()
        
    else:
        results = await semantic_search(query)
        
    return {
        "results": results,
        "mode_used": mode,
        "result_count": len(results),
        "query": query
    }
