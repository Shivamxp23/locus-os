import os
import json
import httpx
import logging

log = logging.getLogger("locus-query-classifier")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CLASSIFIER_PROMPT = """You are the intent classifier for Locus OS.
Classify the user's prompt into one or more of these intents:
- FACTUAL_PERSONAL: Specific facts about the user's life, what they worked on.
- BEHAVIORAL_PATTERN: Asking about habits, avoiding tasks, why they do things.
- KNOWLEDGE_RETRIEVAL: Information they saved, notes, Obsidian vault content.
- TASK_PLANNING: What to do next, schedule, priorities.
- EMOTIONAL_STATE: Checking mood, feelings, tiredness, energy.
- EXTERNAL_KNOWLEDGE: General knowledge, web search needed, NO personal data needed.
- SYNTHESIS: Asking for a summary, weekly review, big picture.
- INFERENCE_REQUEST: "What does this say about me?", deep reasoning.

Available sources: "postgres", "neo4j", "qdrant", "obsidian", "web", "redis_cache"
Temporal scopes: "last_6h", "last_24h", "last_7d", "last_30d", "all_time"

Output MUST be valid JSON, strictly following this schema:
{
  "primary_intent": "INTENT_TYPE",
  "secondary_intents": ["INTENT_TYPE"],
  "sources_required": ["source1", "source2"],
  "temporal_scope": "scope",
  "requires_deep_reasoning": true|false,
  "confidence": 0.9
}
Do not include any explanation or markdown formatting. Only JSON.
"""

async def classify_query(query: str) -> dict:
    if not GROQ_API_KEY:
        log.warning("GROQ_API_KEY not set. Falling back to default classification.")
        return _default_classification()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": CLASSIFIER_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0
                }
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)

            # Fallback if confidence is low
            if result.get("confidence", 1.0) < 0.7:
                result["sources_required"] = ["postgres", "neo4j", "qdrant", "obsidian", "redis_cache"]

            return result
    except Exception as e:
        log.error(f"Classification failed: {e}")
        return _default_classification()

def _default_classification() -> dict:
    return {
        "primary_intent": "KNOWLEDGE_RETRIEVAL",
        "secondary_intents": ["FACTUAL_PERSONAL"],
        "sources_required": ["postgres", "neo4j", "qdrant", "obsidian", "redis_cache"],
        "temporal_scope": "last_7d",
        "requires_deep_reasoning": False,
        "confidence": 0.5
    }
