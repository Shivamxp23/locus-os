# /opt/locus/backend/services/google_calendar.py
# Google Calendar integration — push scheduled tasks as time blocks

import os
import logging
import httpx
from datetime import datetime, date, timedelta

log = logging.getLogger(__name__)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

# Faction → Google Calendar color ID mapping
# See: https://developers.google.com/calendar/api/v3/reference/colors
FACTION_COLORS = {
    "health":     "10",  # Green (Basil)
    "leverage":   "9",   # Blue (Blueberry)
    "craft":      "6",   # Orange (Tangerine)
    "expression": "3",   # Purple (Grape)
}

# Token cache
_access_token = None
_token_expires = None


async def _get_access_token() -> str:
    """Exchange refresh token for access token (cached)"""
    global _access_token, _token_expires

    if _access_token and _token_expires and datetime.now() < _token_expires:
        return _access_token

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": REFRESH_TOKEN,
                "grant_type": "refresh_token",
            }
        )
        r.raise_for_status()
        data = r.json()
        _access_token = data["access_token"]
        _token_expires = datetime.now() + timedelta(seconds=data.get("expires_in", 3500))
        return _access_token


async def _calendar_request(method: str, path: str, json_data=None, params=None) -> dict:
    """Make authenticated Google Calendar API request"""
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.request(
            method,
            f"https://www.googleapis.com/calendar/v3{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=json_data,
            params=params,
        )
        r.raise_for_status()
        return r.json() if r.content else {}


async def get_existing_events(target_date: date) -> list:
    """Get all events for a given date"""
    try:
        time_min = f"{target_date}T00:00:00+05:30"  # IST
        time_max = f"{target_date}T23:59:59+05:30"
        data = await _calendar_request(
            "GET", "/calendars/primary/events",
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
            }
        )
        return data.get("items", [])
    except Exception as e:
        log.warning(f"Failed to read calendar: {e}")
        return []


async def create_task_event(
    title: str,
    faction: str,
    start_time: datetime,
    duration_hours: float,
    description: str = "",
) -> dict:
    """Create a calendar event for a scheduled task"""
    try:
        end_time = start_time + timedelta(hours=duration_hours)
        color_id = FACTION_COLORS.get(faction, "8")  # Default graphite

        event = {
            "summary": f"[{faction.upper()[:3]}] {title}",
            "description": description or f"Locus scheduled task — Faction: {faction}",
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Asia/Kolkata",
            },
            "colorId": color_id,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 5},
                ],
            },
        }

        result = await _calendar_request(
            "POST", "/calendars/primary/events", json_data=event
        )
        log.info(f"Calendar event created: {title} at {start_time}")
        return result
    except Exception as e:
        log.warning(f"Failed to create calendar event: {e}")
        return {"error": str(e)}


async def push_schedule_to_calendar(
    scheduled_tasks: list,
    start_hour: int = 9,
) -> list:
    """
    Push a list of scheduled tasks to Google Calendar.
    
    Args:
        scheduled_tasks: List of dicts with title, faction, estimated_hours
        start_hour: Hour to start scheduling from (default 9 AM)
    
    Returns:
        List of created event results
    """
    today = date.today()
    current_time = datetime(today.year, today.month, today.day, start_hour, 0)
    results = []

    for task in scheduled_tasks:
        duration = task.get("estimated_hours", 1.0)
        result = await create_task_event(
            title=task["title"],
            faction=task["faction"],
            start_time=current_time,
            duration_hours=duration,
        )
        results.append(result)
        # Move to next slot (add 15 min buffer between tasks)
        current_time += timedelta(hours=duration, minutes=15)

    return results


async def health_check() -> bool:
    """Check if Google Calendar API is accessible"""
    try:
        await _get_access_token()
        return True
    except:
        return False
