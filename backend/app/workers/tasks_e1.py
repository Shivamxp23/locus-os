import json
import uuid
import httpx
from datetime import datetime
from app.workers.celery_app import app

@app.task(queue="engine1", bind=True, max_retries=3)
def process_behavioral_event(self, event_data: dict):
    """Engine 1 normalization pipeline — sync version for Celery compatibility."""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_process(event_data))
        finally:
            loop.close()
    except Exception as exc:
        print(f"[Engine1] ERROR: {exc}", flush=True)
        raise self.retry(exc=exc, countdown=60)

async def _process(event_data: dict):
    import os
    import asyncpg

    print(f"[Engine1] Processing event: {event_data.get('type')} from {event_data.get('source')}", flush=True)

    user_id = event_data.get("user_id")
    content = event_data.get("content") or event_data.get("title", "")
    event_type = event_data.get("type", "unknown")
    source = event_data.get("source", "pwa")

    # Step 1: Extract entities via Ollama
    extracted = await _extract_entities(content)
    print(f"[Engine1] Extracted: {extracted}", flush=True)

    # Step 2: Write to PostgreSQL directly via asyncpg
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        event_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO behavioral_events (
                id, user_id, source, event_type, intent,
                raw_content, normalized_content, summary,
                topic_tags, mood_indicator, energy_required, goal_tags,
                signal_weight, created_at, received_at, processed_by_e2
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8,
                $9, $10, $11, $12,
                $13, $14, $15, $16
            )
        """,
            event_id,
            user_id,
            source,
            event_type,
            extracted.get("intent"),
            content,
            content,
            extracted.get("summary"),
            extracted.get("topics", []),
            extracted.get("mood_indicator"),
            extracted.get("energy_required"),
            extracted.get("goal_tags", []),
            1.0,
            datetime.utcnow(),
            datetime.utcnow(),
            False
        )
        await conn.close()
        print(f"[Engine1] Written to PostgreSQL: {event_id}", flush=True)

        # Step 3: Write to Qdrant (async, fire-and-forget via Celery)
        try:
            from app.workers.celery_app import app as celery_app
            celery_app.send_task("app.workers.tasks_e1.log_to_qdrant", kwargs={
                "event_id": event_id,
                "user_id": user_id,
                "content": content,
                "payload": {
                    "source": source,
                    "event_type": event_type,
                    "intent": extracted.get("intent"),
                    "summary": extracted.get("summary"),
                    "topic_tags": extracted.get("topics", []),
                    "created_at": datetime.utcnow().isoformat()
                }
            }, queue="engine1")
        except Exception as qdrant_err:
            print(f"[Engine1] Qdrant queue error: {qdrant_err}", flush=True)

        # Step 4: Write to Obsidian vault
        await _write_obsidian(user_id, event_data, extracted)

    except Exception as e:
        print(f"[Engine1] DB ERROR: {e}", flush=True)
        raise

async def _extract_entities(content: str) -> dict:
    import os
    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
    if not content or len(content.strip()) < 3:
        return {}
    prompt = f"""Extract from this text. Return ONLY valid JSON, no explanation.
Text: "{content}"
Return: {{"topics": [], "mood_indicator": 0.0, "intent": "create", "goal_tags": [], "energy_required": 5, "summary": "one line"}}"""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{ollama_url}/api/generate", json={
                "model": "phi3.5", "prompt": prompt, "stream": False
            })
            if resp.status_code == 200:
                text = resp.json().get("response", "{}")
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
    except Exception as e:
        print(f"[Engine1] Ollama error: {e}", flush=True)
    return {"intent": "create", "summary": content[:100]}

async def _write_obsidian(user_id: str, event_data: dict, extracted: dict):
    import aiofiles
    import os

    today = datetime.utcnow().strftime("%Y-%m-%d")
    vault_base = f"/vault/{user_id}/OS-managed zone/Logs"
    os.makedirs(vault_base, exist_ok=True)
    file_path = f"{vault_base}/{today}.md"

    event_type = event_data.get("type", "event")
    content_line = event_data.get("content") or event_data.get("title", "")
    time_str = datetime.utcnow().strftime("%H:%M")
    topics = ", ".join(extracted.get("topics", []))

    entry = f"\n- {time_str} [{event_type}] {content_line}"
    if topics:
        entry += f" | topics: {topics}"
    entry += "\n"

    if not os.path.exists(file_path):
        async with aiofiles.open(file_path, "w") as f:
            await f.write(f"---\ndate: {today}\nengine: logging\n---\n\n# Daily log — {today}\n\n## Events\n")

    async with aiofiles.open(file_path, "a") as f:
        await f.write(entry)

    print(f"[Engine1] Written to Obsidian: {file_path}", flush=True)

@app.task(queue="engine1")
def log_to_qdrant(event_id: str, user_id: str, content: str, payload: dict):
    import asyncio
    from app.services.qdrant_service import upsert_behavioral_event
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(upsert_behavioral_event(event_id, user_id, content, payload))
    finally:
        loop.close()
