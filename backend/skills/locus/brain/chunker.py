import os
import re
import logging
import asyncio
from typing import Optional
from backend.services.qdrant_service import get_embeddings_batch, ensure_collection, QDRANT_URL, COLLECTION, _stable_id
import httpx

log = logging.getLogger("brain.chunker")

GROQ_KEY = os.getenv("GROQ_API_KEY", "")

_nlp = None
_nlp_lock = asyncio.Lock()

async def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    async with _nlp_lock:
        if _nlp is not None:
            return _nlp
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            log.warning(f"spacy not available: {e}. Fallback used.")
            _nlp = "regex_fallback"
    return _nlp

def strip_markdown(text: str) -> str:
    # Strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
            
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold/italic markers
    text = re.sub(r'(\*\*|\*|__|_)', '', text)
    return text.strip()

async def get_sentences(text: str) -> list[str]:
    nlp = await _get_nlp()
    if nlp == "regex_fallback":
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in parts if s.strip()]
        
    loop = asyncio.get_event_loop()
    def _do():
        doc = nlp(text[:100000])
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    return await loop.run_in_executor(None, _do)

async def is_factual_groq(sentence: str) -> Optional[bool]:
    if not GROQ_KEY:
        return None
        
    prompt = f"Is this sentence a factual statement, idea, or meaningful claim? Reply only YES or NO. Sentence: {sentence}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 5,
                }
            )
            r.raise_for_status()
            res = r.json()["choices"][0]["message"]["content"].strip().upper()
            return "YES" in res
    except Exception:
        return None

def heuristic_factual_check(sentence: str) -> bool:
    words = sentence.split()
    if len(words) <= 8:
        return False
    if sentence.startswith(("#", "-", "*", ">")):
        return False
    return True

async def filter_factual(sentences: list[str]) -> list[str]:
    factual_sentences = []
    
    # Process sequentially or in small batches to not hit rate limits too hard
    # For speed, we'll use heuristic if groq isn't available or fails
    for sentence in sentences:
        # Skip obvious non-propositions immediately
        if not heuristic_factual_check(sentence):
            continue
            
        groq_result = await is_factual_groq(sentence)
        if groq_result is True:
            factual_sentences.append(sentence)
        elif groq_result is None:
            # Fallback
            factual_sentences.append(sentence)
            
    return factual_sentences

async def process_file_into_chunks(file_path: str, content: str, conn) -> int:
    """
    Process file and insert chunks into Postgres & Qdrant.
    Returns number of chunks created.
    """
    clean_text = strip_markdown(content)
    sentences = await get_sentences(clean_text)
    
    if not sentences:
        return 0
        
    propositions = await filter_factual(sentences)
    if not propositions:
        return 0
        
    # Group by max 5
    grouped_chunks = []
    for i in range(0, len(propositions), 5):
        chunk_text = " ".join(propositions[i:i+5])
        grouped_chunks.append((i // 5, chunk_text))
        
    if not grouped_chunks:
        return 0
        
    # Batch embedding
    texts = [text for _, text in grouped_chunks]
    vectors = await get_embeddings_batch(texts)
    
    await ensure_collection()
    
    points = []
    records = []
    
    for (chunk_index, text), vector in zip(grouped_chunks, vectors):
        if not vector:
            continue
            
        point_id_int = _stable_id(f"{file_path}_{chunk_index}")
        point_id_str = str(point_id_int)
        
        points.append({
            "id": point_id_int,
            "vector": vector,
            "payload": {
                "source_file": file_path,
                "chunk_index": chunk_index,
                "text": text,
                "char_count": len(text)
            }
        })
        records.append((file_path, chunk_index, text, point_id_str))
        
    if points:
        # Push to Qdrant
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.put(
                f"{QDRANT_URL}/collections/{COLLECTION}/points",
                json={"points": points}
            )
            if r.status_code not in (200, 201):
                log.error(f"Qdrant batch upsert failed: {r.text}")
                
        # Push to Postgres
        await conn.executemany("""
            INSERT INTO vault_chunks (file_path, chunk_index, text, qdrant_point_id)
            VALUES ($1, $2, $3, $4)
        """, records)
        
    return len(points)
