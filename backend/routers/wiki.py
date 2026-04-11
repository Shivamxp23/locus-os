from fastapi import APIRouter
router = APIRouter()

@router.get("/wiki/query")
async def wiki_query(q: str = ""):
    return {"answer": f"Wiki query for '{q}' — knowledge base still compiling.", "query": q}
