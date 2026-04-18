# /opt/locus/backend/routers/auth.py
# Google OAuth + Calendar integration

from fastapi import APIRouter
import httpx
import os

router = APIRouter()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://api.locusapp.online/auth/google/callback")


@router.get("/auth/google")
async def google_login():
    """Redirect URI for Google OAuth consent screen"""
    scopes = "https://www.googleapis.com/auth/calendar"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scopes}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {"auth_url": url}


@router.get("/auth/google/callback")
async def google_callback(code: str = ""):
    """Exchange authorization code for tokens"""
    if not code:
        return {"status": "error", "message": "No authorization code provided"}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            }
        )

    if r.status_code != 200:
        return {"status": "error", "detail": r.text}

    data = r.json()
    # In production, save the refresh_token to .env or a secure store
    return {
        "status": "ok",
        "access_token": data.get("access_token", "")[:20] + "...",
        "refresh_token": data.get("refresh_token", "present" if data.get("refresh_token") else "none"),
        "message": "Save the refresh_token to your .env file as GOOGLE_REFRESH_TOKEN"
    }


@router.get("/auth/calendar/status")
async def calendar_status():
    """Check if Google Calendar is connected"""
    from services.google_calendar import health_check
    connected = await health_check()
    return {"connected": connected}
