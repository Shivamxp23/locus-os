"""
context_synthesizer.py — System 1.3: Context Synthesizer

Merges all parallel retrieval results into a single coherent context
block for the LLM, respecting token budgets per layer.

Token Budget (800 total):
- Identity layer: 80 tokens
- Temporal layer: 60 tokens
- PostgreSQL layer: 180 tokens
- Neo4j layer: 150 tokens
- Qdrant/Obsidian layer: 200 tokens
- Web layer: 100 tokens
- Overflow buffer: 30 tokens

If ALL layers return empty, the context explicitly tells the LLM
"No relevant personal data found" to prevent hallucination.
"""

import json
from datetime import datetime
from typing import Dict, Any

from core.shorthand import (
    encode_daily_log, encode_task, encode_task_deferred,
    encode_faction_score, SHORTHAND_SCHEMA_PROMPT
)

import logging
log = logging.getLogger("locus-context-synthesizer")

# Approximate: 1 token ≈ 4 chars. Budget in chars.
CHAR_BUDGET = {
    "identity": 320,     # 80 tokens
    "temporal": 240,     # 60 tokens
    "postgres": 720,     # 180 tokens
    "neo4j": 600,        # 150 tokens
    "semantic": 800,     # 200 tokens
    "web": 400,          # 100 tokens
}


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, respecting word boundaries."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last space to avoid mid-word cut
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.7:
        return truncated[:last_space] + "…"
    return truncated + "…"


def _compress_postgres(pg_data: dict) -> str:
    """Compress PostgreSQL data using LOCUS_SHORTHAND."""
    parts = []

    # Daily logs → shorthand
    for event in pg_data.get("events", []):
        if event.get("type") == "daily_log":
            parts.append(encode_daily_log(event))

    # Current DCS
    dcs = pg_data.get("current_dcs")
    if dcs:
        parts.append(f"TODAY: dcs={dcs.get('dcs')} mode={dcs.get('mode')} mood={dcs.get('mood')} e={dcs.get('energy')}")

    # Tasks → shorthand
    for task in pg_data.get("tasks", [])[:5]:
        parts.append(encode_task(task))

    # Deferred tasks
    for d in pg_data.get("deferred_tasks", [])[:3]:
        parts.append(encode_task_deferred(
            d.get("title", "?")[:15],
            d.get("deferral_count", 0),
            d.get("reason", "unknown") or "unknown"
        ))

    # Faction scores
    factions = pg_data.get("faction_scores", [])
    if factions:
        faction_dict = {f["faction"]: f.get("actual_hours", 0) for f in factions}
        parts.append(encode_faction_score(
            faction_dict.get("health", 0),
            faction_dict.get("leverage", 0),
            faction_dict.get("craft", 0),
            faction_dict.get("expression", 0),
        ))

    # Mood trend
    if pg_data.get("mood_trend"):
        parts.append(f"mood_trend:{pg_data['mood_trend']}")

    return " ".join(parts) if parts else ""


def _compress_neo4j(neo4j_data: dict) -> str:
    """Compress Neo4j graph data into structured text."""
    parts = []

    traits = neo4j_data.get("traits", [])
    if traits:
        trait_str = ", ".join(t["name"] if isinstance(t, dict) else str(t) for t in traits[:5])
        parts.append(f"Traits: {trait_str}")

    patterns = neo4j_data.get("patterns", [])
    if patterns:
        for p in patterns[:3]:
            if isinstance(p, dict):
                parts.append(f"Pattern({p.get('type','?')}): {p.get('description', '')[:60]}")
            else:
                parts.append(f"Pattern: {str(p)[:60]}")

    avoidances = neo4j_data.get("avoidances", [])
    if avoidances:
        avoid_str = ", ".join(
            a["description"][:30] if isinstance(a, dict) else str(a)[:30]
            for a in avoidances[:3]
        )
        parts.append(f"Avoidances: {avoid_str}")

    pathways = neo4j_data.get("pathways", [])
    if pathways:
        for pw in pathways[:3]:
            parts.append(
                f"Pathway: -{pw['relationship']}->{pw['target_type']}:{pw['target']} (w={pw['weight']:.2f})"
            )

    projects = neo4j_data.get("active_projects", [])
    if projects:
        parts.append(f"Active projects: {', '.join(projects[:5])}")

    return "\n".join(parts) if parts else ""


def _compress_semantic(qdrant_data: list, obsidian_data: list) -> str:
    """Merge and compress Qdrant + Obsidian retrieval results."""
    parts = []

    for item in obsidian_data:
        if isinstance(item, dict):
            source = item.get("source", "vault")
            content = item.get("content", "")[:150]
            if content:
                parts.append(f"[{source}] {content}")

    for item in qdrant_data:
        if isinstance(item, dict):
            text = item.get("text", "")[:120]
            fname = item.get("filename", "")
            score = item.get("score", 0)
            if text:
                short_name = fname.split("/")[-1] if fname else ""
                parts.append(f"[qdrant:{short_name}|{score}] {text}")

    return "\n".join(parts) if parts else ""


def synthesize_context(retrieved_data: Dict[str, Any], routing_info: Dict[str, Any]) -> str:
    """
    Merge all retrieved data into a single context block for the LLM.

    Returns None if context synthesis fails (triggers error message in bot).
    Returns the full context string on success.
    """
    if not retrieved_data:
        return None

    context_parts = []
    all_empty = True

    # ── Metadata header ──
    now = datetime.now().astimezone()
    sources_used = [k for k, v in retrieved_data.items() if v]
    confidence = routing_info.get("confidence", 0.8)
    scope = routing_info.get("temporal_scope", "last_7d")

    header = (
        f"[CONTEXT_META]\n"
        f"sources_used: {', '.join(sources_used)}\n"
        f"temporal_scope: {scope}\n"
        f"data_confidence: {confidence}\n"
        f"retrieved_at: {now.isoformat()}\n"
        f"[/CONTEXT_META]"
    )
    context_parts.append(header)

    # ── Temporal layer (60 tokens) ──
    day_of_week = now.strftime("%A")
    time_str = now.strftime("%H:%M")
    temporal = f"[TEMPORAL] {now.strftime('%Y-%m-%d')} {day_of_week} {time_str} IST"
    context_parts.append(_truncate(temporal, CHAR_BUDGET["temporal"]))

    # ── Redis / Identity layer (80 tokens) ──
    redis_data = retrieved_data.get("redis_cache") or {}
    if redis_data:
        current_state = redis_data.get("current_state", {})
        if current_state:
            all_empty = False
            # Extract key state fields
            psych = current_state.get("psychological_state", {})
            ops = current_state.get("operational_state", {})
            state_parts = []
            if psych.get("mood_value"):
                state_parts.append(f"mood:{psych['mood_value']}/10({psych.get('mood_trend','')})")
            if psych.get("energy_level"):
                state_parts.append(f"energy:{psych['energy_level']}/10")
            if ops.get("momentum"):
                state_parts.append(f"momentum:{ops['momentum']}")
            if ops.get("tasks_completed_today") is not None:
                state_parts.append(f"done_today:{ops['tasks_completed_today']}")
            if ops.get("deferral_rate_7d") is not None:
                state_parts.append(f"defer_rate_7d:{ops['deferral_rate_7d']:.0%}")

            identity_str = f"[STATE] {' '.join(state_parts)}"
            context_parts.append(_truncate(identity_str, CHAR_BUDGET["identity"]))

    # ── PostgreSQL layer (180 tokens) ──
    pg_data = retrieved_data.get("postgres") or {}
    if pg_data:
        pg_str = _compress_postgres(pg_data)
        if pg_str:
            all_empty = False
            context_parts.append(f"[POSTGRES]\n{_truncate(pg_str, CHAR_BUDGET['postgres'])}")

    # ── Neo4j layer (150 tokens) ──
    neo4j_data = retrieved_data.get("neo4j") or {}
    if neo4j_data:
        neo4j_str = _compress_neo4j(neo4j_data)
        if neo4j_str:
            all_empty = False
            context_parts.append(f"[NEO4J]\n{_truncate(neo4j_str, CHAR_BUDGET['neo4j'])}")

    # ── Semantic layer: Qdrant + Obsidian (200 tokens) ──
    qdrant_data = retrieved_data.get("qdrant") or []
    obsidian_data = retrieved_data.get("obsidian") or []
    if qdrant_data or obsidian_data:
        semantic_str = _compress_semantic(qdrant_data, obsidian_data)
        if semantic_str:
            all_empty = False
            context_parts.append(f"[SEMANTIC]\n{_truncate(semantic_str, CHAR_BUDGET['semantic'])}")

    # ── Web layer (100 tokens) ──
    web_data = retrieved_data.get("web") or []
    if web_data:
        web_parts = []
        for w in web_data[:3]:
            if isinstance(w, dict):
                web_parts.append(f"{w.get('title', '')}: {w.get('snippet', '')}")
        if web_parts:
            web_str = "\n".join(web_parts)
            context_parts.append(f"[WEB]\n{_truncate(web_str, CHAR_BUDGET['web'])}")

    # ── No data warning ──
    if all_empty:
        context_parts.append(
            "\n[NO_PERSONAL_DATA] No relevant personal data found in any source. "
            "Answer from general knowledge but STATE CLEARLY that this is NOT based "
            "on Shivam's personal data. Do not fabricate personal information."
        )

    return "\n\n".join(context_parts)
