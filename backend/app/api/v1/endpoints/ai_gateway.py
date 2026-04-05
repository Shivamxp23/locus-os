from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from pydantic import ConfigDict
from typing import Optional, List
from datetime import datetime
import httpx
import uuid
import time
import logging
from app.database import get_db
from app.models.models import User, AiConversation
from app.services.auth import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    messages: List[Message]
    model_preference: Optional[str] = None


@router.post("/chat")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages = [m.model_dump() for m in req.messages]
    response_text, model_used, model_source = await _route_llm(messages)

    convo = AiConversation(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        model_used=model_used,
        model_source=model_source,
        messages=messages + [{"role": "assistant", "content": response_text}],
        created_at=datetime.utcnow(),
    )
    db.add(convo)
    await db.commit()

    return {"response": response_text, "model": model_used, "source": model_source}


@router.post("/voice")
async def voice_note(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.voice import transcribe_voice

    audio_data = await file.read()
    transcription = await transcribe_voice(audio_data, file.filename or "voice.ogg")

    if not transcription:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    return {"transcription": transcription, "status": "logged"}


async def _call_ollama(
    messages: list, model: str = "llama3.1:8b"
) -> tuple[str, str, str]:
    """Call Ollama with 8 second timeout. Returns (response_text, model_used, source)."""
    start = time.time()
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        elapsed = time.time() - start
        logger.info(f"Ollama response in {elapsed:.2f}s using {model}")
        return resp.json()["message"]["content"], model, "ollama"


async def _call_groq(messages: list) -> tuple[str, str, str]:
    """Call Groq as fallback. Returns (response_text, model_used, source)."""
    start = time.time()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={"model": "llama-3.1-70b-versatile", "messages": messages},
        )
        resp.raise_for_status()
        elapsed = time.time() - start
        logger.info(f"Groq response in {elapsed:.2f}s using llama-3.1-70b-versatile")
        return (
            resp.json()["choices"][0]["message"]["content"],
            "llama-3.1-70b-versatile",
            "groq",
        )


async def _route_llm(messages: list) -> tuple[str, str, str]:
    """
    AI Gateway routing with clean fallback:
    1. Try Ollama (8s timeout)
    2. If exception OR timeout → retry Ollama once
    3. If retry fails → fall back to Groq
    Logs which model was used on every call.
    """
    # First attempt: Ollama
    try:
        return await _call_ollama(messages)
    except Exception as e:
        logger.warning(f"Ollama first attempt failed: {e}")

    # Second attempt: retry Ollama once
    try:
        logger.info("Retrying Ollama (second attempt)")
        return await _call_ollama(messages)
    except Exception as e:
        logger.warning(f"Ollama retry failed: {e}")

    # Final fallback: Groq
    if settings.GROQ_API_KEY:
        try:
            logger.info("Falling back to Groq")
            return await _call_groq(messages)
        except Exception as e:
            logger.error(f"Groq fallback failed: {e}")

    logger.error("All AI services unavailable")
    return "All AI services are currently unavailable.", "none", "none"


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List user's AI conversation history."""
    from sqlalchemy import select

    result = await db.execute(
        select(AiConversation)
        .where(AiConversation.user_id == current_user.id)
        .order_by(AiConversation.created_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "model_used": c.model_used,
            "model_source": c.model_source,
            "summary": c.summary,
            "topic_tags": c.topic_tags or [],
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation with messages."""
    from sqlalchemy import select

    result = await db.execute(
        select(AiConversation).where(
            AiConversation.id == conversation_id,
            AiConversation.user_id == current_user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": str(convo.id),
        "model_used": convo.model_used,
        "model_source": convo.model_source,
        "messages": convo.messages,
        "summary": convo.summary,
        "topic_tags": convo.topic_tags or [],
        "token_count": convo.token_count,
        "created_at": convo.created_at.isoformat() if convo.created_at else None,
        "obsidian_path": convo.obsidian_path,
    }
