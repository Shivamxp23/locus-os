# /opt/locus/backend/services/proposition_chunker.py
# Proposition-based chunking for vault files.
#
# Algorithm:
#   1. Strip YAML frontmatter
#   2. Split into sentences (spacy en_core_web_sm)
#   3. For each sentence, ask LLM classifier:
#      "Is this a standalone factual proposition?"
#      Groq llama-3.1-8b-instant (fast, free tier)
#   4. Keep only sentences where LLM returns non-null
#   5. Group consecutive propositions into chunks of MAX 5
#   6. Each chunk → one Qdrant point

import os
import re
import logging
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import httpx

log = logging.getLogger("locus-chunker")

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")
MAX_PROPOSITIONS_PER_CHUNK = 5

# ── spacy loader (lazy, thread-safe) ─────────────────────────────────────────

_nlp = None
_nlp_lock = asyncio.Lock()


async def _get_nlp():
    """Lazy-load spacy model. Falls back to regex if spacy unavailable."""
    global _nlp
    if _nlp is not None:
        return _nlp
    async with _nlp_lock:
        if _nlp is not None:
            return _nlp
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
            log.info("spacy en_core_web_sm loaded")
        except (ImportError, OSError) as e:
            log.warning(f"spacy unavailable ({e}), using regex sentence splitting")
            _nlp = "regex_fallback"
    return _nlp


def _split_sentences_regex(text: str) -> list[str]:
    """Regex fallback for sentence splitting."""
    # Split on sentence-ending punctuation followed by whitespace + uppercase
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 10]


async def split_sentences(text: str) -> list[str]:
    """Split text into sentences using spacy or regex fallback."""
    nlp = await _get_nlp()
    if nlp == "regex_fallback":
        return _split_sentences_regex(text)

    loop = asyncio.get_event_loop()
    # spacy is CPU-bound; run in executor
    def _do():
        doc = nlp(text[:100000])  # limit to 100k chars
        return [sent.text.strip() for sent in doc.sents
                if sent.text.strip() and len(sent.text.strip()) > 10]
    return await loop.run_in_executor(None, _do)


# ── Frontmatter parsing ─────────────────────────────────────────────────────

def strip_frontmatter(content: str) -> tuple[dict, str]:
    """
    Strip YAML frontmatter from markdown content.
    Returns (frontmatter_dict, body_text).
    """
    fm = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            # Parse simple key: value pairs
            for line in fm_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    # Handle list values like tags: [a, b] or tags: a, b
                    if val.startswith("[") and val.endswith("]"):
                        val = [v.strip().strip('"').strip("'")
                               for v in val[1:-1].split(",") if v.strip()]
                    fm[key] = val

    # Also strip existing locus annotations
    if "## ⟨locus⟩" in body:
        body = body[:body.index("## ⟨locus⟩")].strip()

    return fm, body


def extract_tags(frontmatter: dict) -> list[str]:
    """Extract tags from frontmatter."""
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip().strip("#") for t in tags.split(",") if t.strip()]
    elif isinstance(tags, list):
        tags = [str(t).strip().strip("#") for t in tags if t]
    return tags


def extract_locus_managed(frontmatter: dict) -> bool:
    """Check if file is locus_managed from frontmatter."""
    val = frontmatter.get("locus_managed", "false")
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "yes", "1")


# ── LLM Classifier ──────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = (
    "Is this sentence a complete standalone factual proposition? "
    "If yes, return it as-is. If no (e.g. headings, fragments, "
    "metadata, questions without answers, filler), return ONLY the word null."
)


async def _classify_via_groq(sentence: str) -> Optional[str]:
    """Classify sentence as proposition via Groq (fast, free tier)."""
    if not GROQ_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": CLASSIFIER_PROMPT},
                        {"role": "user", "content": sentence},
                    ],
                    "temperature": 0,
                    "max_tokens": 10,
                },
            )
            r.raise_for_status()
            result = r.json()["choices"][0]["message"]["content"].strip()
            if result.lower() == "null" or result.lower() == "none":
                return None
            return sentence  # The sentence IS a proposition
    except Exception as e:
        log.warning(f"Groq classify failed: {e}")
        return None


async def _classify_via_ollama(sentence: str) -> Optional[str]:
    """Classify sentence as proposition via Ollama phi3.5 (local, free)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "phi3.5",
                    "prompt": f"{CLASSIFIER_PROMPT}\n\nSentence: {sentence}",
                    "stream": False,
                },
            )
            r.raise_for_status()
            result = r.json()["response"].strip()
            if result.lower() == "null" or result.lower() == "none":
                return None
            return sentence
    except Exception:
        return None


async def classify_sentence(sentence: str) -> Optional[str]:
    """
    Classify: try Ollama first (free, local), fallback to Groq.
    Returns the sentence if it's a proposition, None otherwise.
    """
    # Try Ollama first (local, no API limit)
    result = await _classify_via_ollama(sentence)
    if result is not None:
        return result
    # Fallback to Groq
    return await _classify_via_groq(sentence)


async def classify_sentences_batch(sentences: list[str]) -> list[str]:
    """
    Classify a batch of sentences. Uses concurrent requests with rate limiting.
    Returns only the sentences that are valid propositions.
    """
    if not sentences:
        return []

    # For efficiency: run in batches of 10 concurrent
    propositions = []
    batch_size = 10

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        results = await asyncio.gather(
            *[classify_sentence(s) for s in batch],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, str) and r:
                propositions.append(r)
        # Rate limit between batches
        if i + batch_size < len(sentences):
            await asyncio.sleep(0.5)

    return propositions


# ── Chunking ─────────────────────────────────────────────────────────────────

def group_propositions(propositions: list[str], max_per_chunk: int = MAX_PROPOSITIONS_PER_CHUNK) -> list[list[str]]:
    """Group consecutive propositions into chunks of max_per_chunk."""
    if not propositions:
        return []
    chunks = []
    for i in range(0, len(propositions), max_per_chunk):
        chunks.append(propositions[i:i + max_per_chunk])
    return chunks


# ── Main entry point ─────────────────────────────────────────────────────────

async def chunk_file(file_path: Path) -> list[dict]:
    """
    Process a vault .md file into proposition-based chunks.

    Returns a list of chunk payloads ready for Qdrant upsert:
    [
        {
            "file_path": str,
            "vault_section": str,
            "chunk_index": int,
            "propositions": list[str],
            "chunk_text": str,
            "file_modified_at": str,
            "tags": list[str],
            "locus_managed": bool,
        },
        ...
    ]
    """
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = strip_frontmatter(content)

    if len(body.strip()) < 20:
        return []

    # Extract metadata
    tags = extract_tags(frontmatter)
    locus_managed = extract_locus_managed(frontmatter)
    file_mod = datetime.fromtimestamp(
        file_path.stat().st_mtime, tz=timezone.utc
    ).isoformat()

    # Determine vault section from path
    vault_root = Path("/vault")
    try:
        relative = file_path.relative_to(vault_root)
        vault_section = str(relative.parts[0]) if len(relative.parts) > 1 else "root"
    except ValueError:
        vault_section = "unknown"

    # Split into sentences
    sentences = await split_sentences(body)

    if not sentences:
        return []

    # Classify sentences as propositions
    # For very large files, limit to first 200 sentences to stay within rate limits
    propositions = await classify_sentences_batch(sentences[:200])

    if not propositions:
        # If no propositions found (classifier down or all null), 
        # fall back to treating each sentence as a proposition
        # but limit to meaningful ones (>30 chars)
        propositions = [s for s in sentences if len(s) > 30][:50]

    # Group into chunks
    prop_chunks = group_propositions(propositions)

    # Build payloads
    results = []
    for idx, chunk_props in enumerate(prop_chunks):
        chunk_text = " | ".join(chunk_props)
        payload = {
            "file_path": str(file_path),
            "vault_section": vault_section,
            "chunk_index": idx,
            "propositions": chunk_props,
            "chunk_text": chunk_text,
            "file_modified_at": file_mod,
            "tags": tags,
            "locus_managed": locus_managed,
        }
        results.append(payload)

    return results


def chunk_id(file_path: str, chunk_index: int) -> int:
    """Generate a stable integer ID for a Qdrant point from file path + chunk index."""
    source = f"{file_path}::chunk::{chunk_index}"
    h = hashlib.md5(source.encode()).hexdigest()
    return int(h[:15], 16)
