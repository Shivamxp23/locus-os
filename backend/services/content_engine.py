import os
import json
import logging
import asyncpg
from services.llm import call_llm

log = logging.getLogger("locus-content-engine")
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

async def generate_draft(topic: str) -> str:
    """
    Connects to the internal Postgres and Neo4j (via existing summaries) to pull context
    and streams to Gemini 2.5 Pro to write a highly contextualized draft content.
    """
    conn = await get_conn()
    try:
        # Pull the latest personality snapshot
        row = await conn.fetchrow("""
            SELECT snapshot_data FROM personality_snapshots 
            WHERE user_id = 'shivam' 
            ORDER BY snapshot_date DESC LIMIT 1
        """)
        snapshot = json.loads(row["snapshot_data"]) if row else {}
    except Exception as e:
        log.error(f"Failed to fetch personality snapshot: {e}")
        snapshot = {}
    finally:
        await conn.close()

    system_prompt = (
        "You are Locus OS Content Engine, Shivam's personal AI copywriter. "
        "Shivam is building Locus OS, a Personal Cognitive Operating System. "
        "Write a high-quality, engaging draft based on the topic provided. "
        "Use these insights about his recent behavior/focus to ground the post:\n"
        f"{json.dumps(snapshot, indent=2)}\n\n"
        "Keep the tone authentic, insightful, and slightly technical but accessible."
    )

    log.info(f"Generating draft for topic: {topic}")
    
    try:
        draft = await call_llm(prompt=f"Topic: {topic}\n\nPlease generate the draft now.", task_type="weekly", system=system_prompt)
        return draft
    except Exception as e:
        log.error(f"Draft generation failed: {e}")
        return "Draft generation failed due to an error."
