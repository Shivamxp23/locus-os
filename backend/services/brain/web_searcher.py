import os
import logging
import httpx
from typing import Optional

log = logging.getLogger("brain.web_searcher")

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

async def search_web(query: str) -> dict:
    log.info(f"Performing web search for: {query}")
    
    if not SERPAPI_KEY:
        log.warning("SERPAPI_KEY not set. Returning empty web results.")
        return {
            "query": query,
            "results": [],
            "source": "web"
        }
        
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "engine": "google",
                    "num": 3
                }
            )
            r.raise_for_status()
            data = r.json()
            
            results = []
            for item in data.get("organic_results", [])[:3]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", "")
                })
                
            return {
                "query": query,
                "results": results,
                "source": "web"
            }
    except Exception as e:
        log.error(f"Web search failed: {e}")
        return {
            "query": query,
            "results": [],
            "source": "web"
        }
