import httpx

LIGHTRAG_URL = "http://localhost:9621"

async def query_brain(question: str, mode: str = "hybrid") -> dict:
    """
    mode: hybrid (default) | local (specific facts) | global (patterns/themes)
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{LIGHTRAG_URL}/query",
                json={"query": question, "mode": mode, "stream": False})
            if r.status_code == 200:
                return {"status": "ok", "answer": r.json().get("response", "")}
    except Exception as e:
        return {"status": "unavailable", "answer": None, "error": str(e)}
    return {"status": "error", "answer": None}

async def health_check() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            return (await client.get(f"{LIGHTRAG_URL}/health")).status_code == 200
    except: return False
