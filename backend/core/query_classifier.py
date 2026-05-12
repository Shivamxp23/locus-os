"""
query_classifier.py — System 1.1: Intent Classification

Classifies every incoming prompt into intent types + required data sources
using a single lightweight Groq 8b-instant call (~50 tokens).

This is the FIRST step in the routing pipeline. It determines what data
Locus needs to look at before the LLM even sees the question.
"""

import os
import json
import httpx
import logging
from datetime import datetime

log = logging.getLogger("locus-query-classifier")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CLASSIFIER_PROMPT = """You are Locus OS's intent classifier. Your job is to determine what kind of question this is and what data sources to query.

INTENT TYPES:
- FACTUAL_PERSONAL: Facts about the user's life, what they did, specific events. → postgres, neo4j
- BEHAVIORAL_PATTERN: Why they do things, habits, avoidance, recurring behaviors. → neo4j, qdrant, postgres
- KNOWLEDGE_RETRIEVAL: Something the user saved, notes, vault content, "what do I know about X". → obsidian, qdrant
- TASK_PLANNING: What to do next, priorities, schedule, energy-based suggestions. → postgres, neo4j, redis_cache
- EMOTIONAL_STATE: Mood, feelings, tiredness, energy, "I feel X". → postgres, neo4j, redis_cache
- EXTERNAL_KNOWLEDGE: General knowledge about the world, "what is X technology". → web (NO personal data needed)
- SYNTHESIS: Summary, weekly review, big picture, "how's my week going". → postgres, neo4j, qdrant, obsidian, redis_cache
- INFERENCE_REQUEST: "What does this say about me?", deep reasoning about self. → postgres, neo4j, qdrant, obsidian, redis_cache

AVAILABLE SOURCES: "postgres", "neo4j", "qdrant", "obsidian", "web", "redis_cache"
TEMPORAL SCOPES: "last_6h", "last_24h", "last_7d", "last_30d", "all_time"

Rules:
- Most personal questions need BOTH postgres AND neo4j at minimum
- If the question mentions time ("today", "this week", "yesterday"), set appropriate temporal_scope
- EMOTIONAL_STATE and BEHAVIORAL_PATTERN always need redis_cache for current state
- EXTERNAL_KNOWLEDGE is the ONLY intent that doesn't need personal data sources
- If unsure, include more sources rather than fewer
- requires_deep_reasoning = true for INFERENCE_REQUEST, SYNTHESIS, and complex BEHAVIORAL_PATTERN

Return ONLY valid JSON:
{
  "primary_intent": "INTENT_TYPE",
  "secondary_intents": ["INTENT_TYPE"],
  "sources_required": ["source1", "source2"],
  "temporal_scope": "last_7d",
  "requires_deep_reasoning": false,
  "confidence": 0.9
}"""


async def classify_query(query: str) -> dict:
    """
    Classify user query into intent type + required data sources.
    Uses Groq 8b-instant for speed (~50 tokens, <500ms).
    Falls back to querying ALL sources on any failure.
    """
    if not GROQ_API_KEY:
        log.warning("GROQ_API_KEY not set. Defaulting to all-source retrieval.")
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
                    "temperature": 0.0,
                    "max_tokens": 150,
                }
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)

            # Validate required fields
            if "primary_intent" not in result:
                return _default_classification()

            # Safety: if confidence is low, query everything
            if result.get("confidence", 1.0) < 0.7:
                result["sources_required"] = [
                    "postgres", "neo4j", "qdrant", "obsidian", "redis_cache"
                ]

            # Ensure sources_required is always a list
            if not isinstance(result.get("sources_required"), list):
                result["sources_required"] = [
                    "postgres", "neo4j", "qdrant", "obsidian", "redis_cache"
                ]

            return result

    except Exception as e:
        log.error(f"Classification failed: {e}")
        return _default_classification()


def _default_classification() -> dict:
    """Fallback: query ALL personal data sources."""
    return {
        "primary_intent": "SYNTHESIS",
        "secondary_intents": ["FACTUAL_PERSONAL", "KNOWLEDGE_RETRIEVAL"],
        "sources_required": ["postgres", "neo4j", "qdrant", "obsidian", "redis_cache"],
        "temporal_scope": "last_7d",
        "requires_deep_reasoning": False,
        "confidence": 0.5
    }
