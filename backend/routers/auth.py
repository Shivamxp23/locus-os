from fastapi import APIRouter
router = APIRouter()

@router.get("/auth/google/callback")
async def google_callback(code: str = ""):
    return {"status": "ok"}
