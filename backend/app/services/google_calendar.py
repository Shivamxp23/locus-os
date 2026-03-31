"""
Google Calendar service — OAuth 2.0 flow + event read.
Spec: §20.1
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import httpx
from app.config import settings


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

SCOPES = "https://www.googleapis.com/auth/calendar.readonly"


def get_auth_url(state: str = "") -> str:
    """Build the Google OAuth consent URL."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an OAuth auth code for access + refresh tokens."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> Optional[str]:
    """Use a refresh token to get a new access token."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            if resp.status_code == 200:
                return resp.json().get("access_token")
    except Exception as e:
        print(f"[GoogleCal] Token refresh error: {e}", flush=True)
    return None


async def fetch_upcoming_events(access_token: str, max_results: int = 20) -> list:
    """Fetch the next N upcoming events from the user's primary calendar."""
    now = datetime.utcnow().isoformat() + "Z"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(CALENDAR_EVENTS_URL, headers={
                "Authorization": f"Bearer {access_token}"
            }, params={
                "timeMin": now,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            })
            if resp.status_code == 200:
                return resp.json().get("items", [])
    except Exception as e:
        print(f"[GoogleCal] Fetch events error: {e}", flush=True)
    return []
