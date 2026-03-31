from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from pydantic import ConfigDict
from typing import Optional, List
from datetime import datetime
import httpx
import uuid
from app.database import get_db
from app.models.models import User, AiConversation
from app.services.auth import get_current_user
from app.config import settings

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
    db: AsyncSession = Depends(get_db)
):
    messages = [m.model_dump() for m in req.messages]
    response_text, model_used, model_source = await _route_llm(messages)

    convo = AiConversation(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        model_used=model_used,
        model_source=model_source,
        messages=messages + [{"role": "assistant", "content": response_text}],
        created_at=datetime.utcnow()
    )
    db.add(convo)
    await db.commit()

    try:
        from app.workers.celery_app import app as celery_app
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
            "event_data": {
                "type": "ai_chat",
                "user_id": current_user.id,
                "source": "ai_gateway",
                "content": last_user_msg,
                "created_at": datetime.utcnow().isoformat()
            }
        }, queue="engine1")
    except Exception:
        pass

    return {"response": response_text, "model": model_used, "source": model_source}

@router.post("/voice")
async def voice_note(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.voice import transcribe_voice
    audio_data = await file.read()
    transcription = await transcribe_voice(audio_data, file.filename or "voice.ogg")

    if not transcription:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    try:
        from app.workers.celery_app import app as celery_app
        celery_app.send_task("app.workers.tasks_e1.process_behavioral_event", kwargs={
            "event_data": {
                "type": "voice_note",
                "user_id": current_user.id,
                "source": "pwa",
                "content": transcription,
                "created_at": datetime.utcnow().isoformat()
            }
        }, queue="engine1")
    except Exception:
        pass

    return {"transcription": transcription, "status": "logged"}

async def _route_llm(messages: list) -> tuple[str, str, str]:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{settings.OLLAMA_URL}/api/chat", json={
                "model": "llama3.1:8b",
                "messages": messages,
                "stream": False
            })
            if resp.status_code == 200:
                return resp.json()["message"]["content"], "llama3.1:8b", "ollama"
    except Exception:
        pass

    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            response = model.generate_content(prompt)
            return response.text, "gemini-2.0-flash", "gemini"
        except Exception:
            pass

    if settings.GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={"model": "llama-3.1-8b-instant", "messages": messages}
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"], "llama-3.1-8b-instant", "groq"
        except Exception:
            pass

    return "All AI services are currently unavailable.", "none", "none"
