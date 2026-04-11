from fastapi import APIRouter, Header, HTTPException
import os, logging

router = APIRouter()

SERVICE_TOKEN = os.getenv("LOCUS_SERVICE_TOKEN")

def _check(token):
    if token != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/vault/search")
async def vault_search(q: str = "", x_service_token: str = Header(None)):
    _check(x_service_token)
    if not q or not q.strip():
        return {"results": [], "query": q}

    try:
        import chromadb
        client = chromadb.HttpClient(host="chromadb", port=8000)
        collection = client.get_collection("locus_mempalace")
        results = collection.query(query_texts=[q], n_results=5)

        formatted = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            title = (
                meta.get("title")
                or meta.get("source")
                or meta.get("file_path", "").split("/")[-1].replace(".md", "")
                or f"Note {i+1}"
            )
            excerpt = doc[:400].replace("\n", " ").strip()
            if len(doc) > 400:
                excerpt += "..."
            formatted.append({
                "title": title,
                "excerpt": excerpt,
                "source": meta.get("file_path", ""),
                "score": round(float(distances[i]), 4) if i < len(distances) else 0
            })

        return {"results": formatted, "query": q}

    except Exception as e:
        logging.warning(f"Vault search failed: {e}")
        return {"results": [], "query": q, "error": str(e)}
