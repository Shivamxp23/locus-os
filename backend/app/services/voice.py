import httpx
from app.config import settings

async def transcribe_voice(audio_data: bytes, filename: str = "voice.ogg") -> str:
    """Transcribe audio using Groq Whisper API."""
    if not settings.GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files={"file": (filename, audio_data, "audio/ogg")},
                data={"model": "whisper-large-v3", "response_format": "text"}
            )
            if resp.status_code == 200:
                return resp.text.strip()
    except Exception:
        pass
    return ""
