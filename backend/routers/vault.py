from fastapi import APIRouter
from services.lightrag_service import query_brain, health_check

router = APIRouter()

@router.get("/vault/search")
async def vault_search(q: str = ""):
    if not q: return {"results": [], "query": q}
    result = await query_brain(q, mode="hybrid")
    if result["status"] == "ok" and result["answer"]:
        return {"results": [{"title": "Brain", "excerpt": result["answer"], "score": 1.0}], "query": q}
    return {"results": [], "query": q, "message": "Brain indexing or unavailable."}

@router.get("/wiki/query")
async def wiki_query(q: str = ""):
    if not q: return {"answer": ""}
    result = await query_brain(q, mode="global")
    return {"answer": result.get("answer", "Brain unavailable."), "query": q}

@router.get("/vault/health")
async def vault_health():
    return {"lightrag": "up" if await health_check() else "down"}
