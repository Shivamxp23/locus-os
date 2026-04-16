"""
Vault router — placeholder. Implementation TBD.
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/vault/status")
async def vault_status():
    return {"status": "not implemented"}

@router.post("/vault/search")
async def vault_search():
    return {"answer": "not implemented"}
