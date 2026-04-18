from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncpg
import os

router = APIRouter()
DATABASE_URL = os.getenv("DATABASE_URL")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

@router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="VAPID_PUBLIC_KEY not set on server")
    return {"vapidPublicKey": VAPID_PUBLIC_KEY}

@router.post("/push/subscribe")
async def subscribe_push(sub: PushSubscription):
    try:
        p256dh = sub.keys.get("p256dh")
        auth = sub.keys.get("auth")
        if not p256dh or not auth:
            raise HTTPException(status_code=400, detail="Invalid push subscription keys")
            
        conn = await get_conn()
        await conn.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (endpoint) DO UPDATE SET
                p256dh = EXCLUDED.p256dh,
                auth = EXCLUDED.auth
        """, "shivam", sub.endpoint, p256dh, auth)
        await conn.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
