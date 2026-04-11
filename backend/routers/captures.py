from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class Capture(BaseModel):
    text: str
    source: Optional[str] = "pwa"

@router.post("/captures")
async def create_capture(capture: Capture):
    return {"status": "ok", "message": "Captured ✓"}

@router.get("/captures")
async def get_captures():
    return {"captures": []}
