import json
from datetime import datetime
from typing import Dict, Any
from core.shorthand import encode_mood, encode_sleep, encode_task_deferred, encode_task_done, encode_energy

import logging
log = logging.getLogger("locus-context-synthesizer")

def compress_postgres_data(pg_data: dict) -> str:
    compressed_items = []
    
    for event in pg_data.get("events", []):
        if event.get("type") == "mood":
            compressed_items.append(encode_mood(event.get("mood", 5), event.get("note", "")))
        elif event.get("type") == "sleep":
            compressed_items.append(encode_sleep(event.get("hours", 0), event.get("quality", 5)))
        elif event.get("type") == "task_deferred":
            compressed_items.append(encode_task_deferred(event.get("title", "task")[:10], event.get("deferral_count", 1), event.get("reason", "unknown")))
        elif event.get("type") == "task_done":
            compressed_items.append(encode_task_done(event.get("title", "task")[:10], event.get("duration", 0), event.get("quality", 5)))
        elif event.get("type") == "energy":
            compressed_items.append(encode_energy(event.get("energy", 5), event.get("time", "0000"), event.get("faction", "none")))
    
    return " ".join(compressed_items)

def synthesize_context(retrieved_data: Dict[str, Any], routing_info: Dict[str, Any]) -> str:
    context_parts = []
    
    now = datetime.now().astimezone().isoformat()
    sources_used = [k for k, v in retrieved_data.items() if v]
    confidence = routing_info.get("confidence", 0.8)
    scope = routing_info.get("temporal_scope", "last_7d")
    
    header = f"[CONTEXT_META]\n" \
             f"sources_used: {', '.join(sources_used)}\n" \
             f"temporal_scope: {scope}\n" \
             f"data_confidence: {confidence}\n" \
             f"retrieved_at: {now}\n" \
             f"[/CONTEXT_META]\n"
    context_parts.append(header)
    
    all_empty = True

    day_of_week = datetime.now().strftime("%A")
    temporal_str = f"Current time: {now}, Day: {day_of_week}."
    context_parts.append(f"[TEMPORAL]\n{temporal_str[:240]}\n")
    
    redis_data = retrieved_data.get("redis_cache") or {}
    if redis_data:
        all_empty = False
        identity_str = json.dumps(redis_data.get("identity", {}))
        context_parts.append(f"[IDENTITY]\n{identity_str[:320]}\n")
        
    pg_data = retrieved_data.get("postgres") or {}
    if pg_data:
        all_empty = False
        pg_str = compress_postgres_data(pg_data)
        if not pg_str:
            pg_str = json.dumps(pg_data)
        context_parts.append(f"[POSTGRES_EVENTS]\n{pg_str[:720]}\n")
        
    neo4j_data = retrieved_data.get("neo4j") or {}
    if neo4j_data.get("pathways"):
        all_empty = False
        neo4j_str = json.dumps(neo4j_data["pathways"])
        context_parts.append(f"[NEO4J_PATHWAYS]\n{neo4j_str[:600]}\n")
        
    qdrant_data = retrieved_data.get("qdrant") or []
    obsidian_data = retrieved_data.get("obsidian") or []
    semantic_data = []
    
    for item in obsidian_data:
        semantic_data.append(f"Obsidian: {item.get('content', '')}")
    for item in qdrant_data:
        payload = item.get("payload", {})
        semantic_data.append(f"Note({payload.get('filename','')}): {payload.get('summary', payload.get('text',''))}")
        
    if semantic_data:
        all_empty = False
        semantic_str = "\n".join(semantic_data)
        context_parts.append(f"[SEMANTIC_KNOWLEDGE]\n{semantic_str[:800]}\n")
        
    web_data = retrieved_data.get("web") or []
    if web_data:
        web_str = "\n".join([f"{w.get('title')}: {w.get('snippet')}" for w in web_data])
        context_parts.append(f"[WEB_SEARCH]\n{web_str[:400]}\n")
        
    if all_empty:
        context_parts.append(
            "\n[WARNING] No relevant personal data found. Answer from general knowledge "
            "but state clearly that this is not based on Shivam's personal data."
        )
        
    return "\n".join(context_parts)
