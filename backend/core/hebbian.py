"""
hebbian.py — Hebbian Learning for Neo4j Knowledge Graph

Implements use-dependent strengthening of neural pathways:
1. Every traversal by Source Retriever: edge weight += 0.1
2. Every 👍 signal: session pathway weights × 1.3
3. Every 👎 signal: session pathway weights × 0.7
4. Weekly Sunday decay: all weights × 0.95 (in inner_loop.py)

This creates a self-reinforcing knowledge graph where frequently
accessed and positively-rated pathways become stronger over time.
"""

import os
import json
import logging
from datetime import datetime

from core.db import pg_execute

log = logging.getLogger("locus-hebbian")


async def increment_traversed_weights(pathways: list):
    """
    Called after every Neo4j traversal by the Source Retriever.
    Increments traversed edge weights by 0.1.
    """
    if not pathways:
        return

    try:
        from services.neo4j_service import get_driver
        driver = await get_driver()

        async with driver.session() as s:
            for pw in pathways:
                rel_type = pw.get("relationship", "")
                target = pw.get("target", "")
                if rel_type and target:
                    # Increment weight on the specific edge
                    await s.run(f"""
                        MATCH (p:Person {{name:'Shivam'}})-[r:{rel_type}]->(n)
                        WHERE coalesce(n.name, n.description) = $target
                        SET r.weight = coalesce(r.weight, 0.5) + 0.1
                    """, target=target)

        log.debug(f"Incremented weights on {len(pathways)} pathways")

    except Exception as e:
        log.warning(f"Hebbian weight increment failed: {e}")


async def apply_feedback_signal(
    interaction_id: str,
    signal_type: str,
    pathways: list,
    source: str = "telegram"
):
    """
    Apply Hebbian feedback signal to Neo4j pathway weights.

    Args:
        interaction_id: Unique ID of the interaction being rated
        signal_type: "thumbs_up" or "thumbs_down"
        pathways: List of pathway dicts that were active during this interaction
        source: Where the feedback came from (telegram, pwa, inner_loop)
    """
    multiplier = 1.3 if signal_type == "thumbs_up" else 0.7

    # ── Update Neo4j weights ──
    if pathways:
        try:
            from services.neo4j_service import get_driver
            driver = await get_driver()

            async with driver.session() as s:
                for pw in pathways:
                    rel_type = pw.get("relationship", "")
                    target = pw.get("target", "")
                    if rel_type and target:
                        await s.run(f"""
                            MATCH (p:Person {{name:'Shivam'}})-[r:{rel_type}]->(n)
                            WHERE coalesce(n.name, n.description) = $target
                            SET r.weight = coalesce(r.weight, 0.5) * $mult
                        """, target=target, mult=multiplier)

            log.info(
                f"Hebbian {signal_type}: multiplied {len(pathways)} pathways by {multiplier}"
            )

        except Exception as e:
            log.warning(f"Hebbian Neo4j update failed: {e}")

    # ── Store reward signal in PostgreSQL ──
    try:
        await pg_execute("""
            INSERT INTO reward_signals
                (user_id, interaction_id, signal_type, pathways, source)
            VALUES ('shivam', $1, $2, $3::jsonb, $4)
        """, interaction_id, signal_type, json.dumps(pathways), source)
    except Exception as e:
        log.warning(f"Reward signal save failed: {e}")


async def get_top_pathways(limit: int = 10) -> list:
    """
    Get the top N strongest pathways from Neo4j.
    Used by GET /brain/pathways for PWA display.
    """
    try:
        from services.neo4j_service import get_driver
        driver = await get_driver()

        async with driver.session() as s:
            r = await s.run("""
                MATCH (p:Person {name:'Shivam'})-[r]->(n)
                WHERE r.weight IS NOT NULL AND r.weight > 0.1
                RETURN type(r) AS relationship,
                       labels(n)[0] AS target_type,
                       coalesce(n.name, n.description, 'unnamed') AS target,
                       r.weight AS weight
                ORDER BY r.weight DESC
                LIMIT $limit
            """, limit=limit)

            pathways = [
                {
                    "relationship": rec["relationship"],
                    "target_type": rec["target_type"],
                    "target": rec["target"],
                    "weight": round(rec["weight"], 3),
                }
                async for rec in r
            ]
            return pathways

    except Exception as e:
        log.warning(f"Top pathways fetch failed: {e}")
        return []
