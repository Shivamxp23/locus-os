"""
inference.py — System 2 API Router

Exposes inference endpoints for both the PWA and Telegram bot.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from core.state_engine import infer_current_state
from core.pattern_detector import run_all_horizons
from core.hebbian import apply_feedback_signal, get_top_pathways
from core.db import pg_fetch, redis_get_json

router = APIRouter()
log = logging.getLogger("locus-inference-router")


class InferenceRequest(BaseModel):
    trigger: str
    raw_input: str
    timestamp: str


class FeedbackRequest(BaseModel):
    interaction_id: str
    signal_type: str  # "thumbs_up" or "thumbs_down"
    pathways: list = []
    source: str = "pwa"


@router.post("/inference/explain")
async def explain_inference(req: InferenceRequest):
    """Trigger state inference and return the cause chain."""
    try:
        state = await infer_current_state(req.dict())
        if not state:
            raise HTTPException(status_code=500, detail="Inference engine unavailable.")

        return {
            "status": "ok",
            "inferred_cause_chain": state.get(
                "inferred_cause_chain",
                "Unable to determine cause chain at this moment."
            ),
            "current_state": state
        }
    except Exception as e:
        log.error(f"Inference explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inference/state")
async def get_current_state():
    """Get cached current state from Redis (no LLM call)."""
    state = await redis_get_json("locus:current_state")
    if state:
        return {"status": "ok", "current_state": state}
    return {"status": "ok", "current_state": None, "message": "No state cached. Send a message to trigger inference."}


@router.get("/inference/patterns")
async def get_detected_patterns():
    """Get all active detected patterns."""
    try:
        patterns = await pg_fetch("""
            SELECT pattern_type, description, confidence, horizon,
                   first_detected_at, last_confirmed_at, confirmation_count
            FROM detected_patterns
            WHERE status = 'active'
            ORDER BY confidence DESC
            LIMIT 20
        """)
        return {
            "status": "ok",
            "patterns": [
                {k: (str(v) if hasattr(v, 'isoformat') else v)
                 for k, v in p.items()}
                for p in patterns
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "patterns": []}


@router.get("/inference/pathways")
async def get_pathways():
    """Get top weighted Neo4j pathways (Hebbian)."""
    pathways = await get_top_pathways(limit=15)
    return {"status": "ok", "pathways": pathways}


@router.post("/inference/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit a feedback signal (thumbs up/down) for Hebbian weighting."""
    if req.signal_type not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="signal_type must be 'thumbs_up' or 'thumbs_down'")

    await apply_feedback_signal(
        interaction_id=req.interaction_id,
        signal_type=req.signal_type,
        pathways=req.pathways,
        source=req.source,
    )
    return {"status": "ok", "signal": req.signal_type}


@router.get("/inference/synthesis")
async def get_daily_synthesis():
    """Get recent daily syntheses."""
    try:
        rows = await pg_fetch("""
            SELECT synthesis_date, end_of_day_synthesis, key_insight,
                   recommended_framing, model_used, created_at
            FROM daily_synthesis
            ORDER BY synthesis_date DESC
            LIMIT 7
        """)
        return {
            "status": "ok",
            "syntheses": [
                {k: (str(v) if hasattr(v, 'isoformat') else v)
                 for k, v in r.items()}
                for r in rows
            ]
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "syntheses": []}
