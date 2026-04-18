from fastapi import APIRouter
from services.qdrant_service import direct_search

router = APIRouter()

@router.get("/vector/search")
async def vector_search(q: str = "", limit: int = 5):
    if not q:
        return {"results": [], "query": q}
        
    results = await direct_search(q, limit=limit)
    return {
        "results": results,
        "query": q
    }
