from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from core.state_engine import infer_current_state

router = APIRouter()
log = logging.getLogger("locus-inference-router")

class InferenceRequest(BaseModel):
    trigger: str
    raw_input: str
    timestamp: str

@router.post("/inference/explain")
async def explain_inference(req: InferenceRequest):
    try:
        state = await infer_current_state(req.dict())
        if not state:
            raise HTTPException(status_code=500, detail="Inference engine unavailable.")

        return {
            "status": "ok",
            "inferred_cause_chain": state.get("inferred_cause_chain", "Unable to determine cause chain at this moment."),
            "current_state": state
        }
    except Exception as e:
        log.error(f"Inference explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
