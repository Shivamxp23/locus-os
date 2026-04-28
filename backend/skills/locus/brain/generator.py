import os
import json
import logging
from backend.services.llm import call_llm

log = logging.getLogger("brain.generator")

SYSTEM_PROMPT = """You are Locus, a Personal Cognitive Operating System for one specific user.
Your job is to speak — not to remember, not to guess, not to invent.
You have been given real data retrieved from the user's actual records.
RULES:
1. Answer ONLY from the provided context. If the data is not in the context, say "I don't have that information stored."
2. Never fabricate file contents, task names, syllabi, scores, or any personal data.
3. Be direct. No bullet-pointed generic advice. Speak to this specific person from their specific data.
4. If user_state.mode is SURVIVAL or RECOVERY, match your tone accordingly. Don't push tasks.
5. If the context is empty and the query is personal, respond: "I don't have data on that yet. Would you like to log it?"
6. You are not a therapist. You are a precise cognitive tool. Be warm but stay factual.
"""

def validate_response(response: str, context: dict) -> bool:
    # Anti-hallucination guard
    # In a full implementation, we'd check if proper nouns in response exist in context
    # For now, a simplified check
    return True

async def generate_response(inputs: dict) -> str:
    user_query = inputs.get("user_query", "")
    retrieved_context = inputs.get("retrieved_context", [])
    user_state = inputs.get("user_state", {})
    file_content = inputs.get("file_content")
    schedule = inputs.get("schedule")
    patterns = inputs.get("patterns")
    web_results = inputs.get("web_results")
    instruction = inputs.get("instruction", "Answer the user's query.")
    
    context_blocks = []
    
    if retrieved_context:
        context_blocks.append("--- RETRIEVED DATA ---")
        for i, c in enumerate(retrieved_context):
            context_blocks.append(f"[{i+1}] Source: {c.get('source')} | Score: {c.get('score')} | Data: {c.get('text')}")
            
    if file_content:
        context_blocks.append("--- REQUESTED FILE CONTENT ---")
        context_blocks.append(file_content)
        
    if schedule:
        context_blocks.append("--- GENERATED SCHEDULE ---")
        context_blocks.append(json.dumps(schedule, indent=2))
        
    if patterns:
        context_blocks.append("--- DETECTED PATTERNS ---")
        context_blocks.append(json.dumps(patterns, indent=2))
        
    if web_results:
        context_blocks.append("--- WEB SEARCH RESULTS ---")
        for r in web_results:
            context_blocks.append(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}")
            
    if user_state:
        context_blocks.append("--- USER STATE ---")
        context_blocks.append(json.dumps(user_state, indent=2))
        
    context_str = "\n".join(context_blocks)
    
    prompt = f"""
{context_str}

USER QUERY: {user_query}
INSTRUCTION: {instruction}
"""
    
    # We call the Groq model
    try:
        response = await call_llm(prompt, task_type="realtime", system=SYSTEM_PROMPT)
        
        if not validate_response(response, inputs):
            return "I don't have reliable data on that. Try asking me to search or log it."
            
        return response
    except Exception as e:
        log.error(f"Generation failed: {e}")
        return "I am experiencing a cognitive error. Please check my logs."
