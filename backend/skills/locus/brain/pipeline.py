import logging
from backend.skills.locus.brain.retriever import retrieve
from backend.skills.locus.brain.reader import read_vault_file
from backend.skills.locus.brain.scheduler import generate_schedule
from backend.skills.locus.brain.pattern_engine import run_weekly as get_patterns
from backend.skills.locus.brain.web_searcher import search_web
from backend.skills.locus.brain.generator import generate_response

log = logging.getLogger("brain.pipeline")

async def get_user_state():
    # In a real impl, fetch from db
    # For now, placeholder or partial fetch
    import os
    import asyncpg
    from datetime import date
    try:
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        row = await conn.fetchrow("SELECT dcs, mode FROM daily_logs WHERE date = $1 AND checkin_type = 'morning'", date.today())
        await conn.close()
        if row:
            return {"dcs": row["dcs"], "mode": row["mode"]}
    except Exception:
        pass
    return {"dcs": 5.0, "mode": "NORMAL"}

async def execute_query(query: str) -> str:
    log.info(f"Pipeline executing for query: {query}")
    
    q_lower = query.lower()
    
    inputs = {
        "user_query": query,
        "retrieved_context": [],
        "user_state": await get_user_state(),
        "file_content": None,
        "schedule": None,
        "patterns": None,
        "web_results": None,
        "instruction": "Answer the user's query directly based on the context."
    }
    
    # 1. "read [file]"
    if q_lower.startswith("read ") or q_lower.startswith("what does ") and " say" in q_lower:
        # Extract filename heuristically
        words = query.split()
        filename = ""
        for w in words:
            if w.endswith(".md"):
                filename = w
                break
        if not filename and len(words) > 1:
            filename = words[1]
            if not filename.endswith(".md"):
                filename += ".md"
                
        reader_res = await read_vault_file(filename)
        if reader_res.found:
            inputs["file_content"] = reader_res.content
            inputs["instruction"] = "Answer ONLY from the following document content. If the answer is not in the document, say so. Do not invent."
        else:
            return f"I could not find the file {filename} in the vault."
            
    # 2. "what should I do" -> Scheduler
    elif "what should i do" in q_lower or "schedule" in q_lower:
        inputs["schedule"] = await generate_schedule()
        inputs["instruction"] = "Present the provided schedule to the user. Explain why tasks were chosen based on DCS, Mode, and Patterns."
        
    # 3. "what patterns..." -> Pattern Engine
    elif "pattern" in q_lower and "see in me" in q_lower:
        inputs["patterns"] = await get_patterns()
        inputs["instruction"] = "Summarize the detected patterns for the user. Do not give generic advice."
        
    # 4. External knowledge -> Web Searcher
    elif any(kw in q_lower for kw in ["latest", "current", "what is", "how does", "news", "today"]) and "my" not in q_lower:
        web_res = await search_web(query)
        if web_res.get("results"):
            inputs["web_results"] = web_res["results"]
            inputs["instruction"] = "Answer the query using the provided web search results. Always surface the source URL."
        else:
            # Fallback to general retrieval
            retriever_res = await retrieve(query)
            inputs["retrieved_context"] = retriever_res["results"]
            
    # 5. General -> Retriever
    else:
        retriever_res = await retrieve(query)
        inputs["retrieved_context"] = retriever_res["results"]
        if not inputs["retrieved_context"]:
            inputs["instruction"] = "Tell the user you don't have that information stored. Do NOT hallucinate."

    # Finally, run the generator
    response = await generate_response(inputs)
    return response
