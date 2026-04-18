import os
import json
import logging
from pywebpush import webpush, WebPushException
import asyncpg

log = logging.getLogger("locus-push")

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

async def send_push_notification(user_id: str, title: str, body: str):
    if not VAPID_PRIVATE_KEY:
        log.warning("Push failed: VAPID_PRIVATE_KEY not configured.")
        return

    conn = await get_conn()
    rows = await conn.fetch("SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = $1", user_id)
    await conn.close()

    if not rows:
        log.info(f"No push subscriptions found for user {user_id}")
        return

    payload = json.dumps({"title": title, "body": body})
    
    for row in rows:
        subscription_info = {
            "endpoint": row["endpoint"],
            "keys": {
                "p256dh": row["p256dh"],
                "auth": row["auth"]
            }
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_SUBJECT}
            )
            log.info(f"Pushed to {row['endpoint']}")
        except WebPushException as ex:
            log.error(f"Push failed: {repr(ex)}")
            # In a real app we might delete stale subscriptions here, but for now we keep it simple.
