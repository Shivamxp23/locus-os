import httpx, os

GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")

async def call_llm(prompt: str, task_type: str = "realtime", system: str = "") -> str:
    """
    5-provider LLM cascade. All free tier.

    task_type:
      - realtime: Groq (fast, fallback to Cerebras)
      - weekly: Gemini 2.5 Pro (1M context)
      - nightly: Cerebras 70B
      - reasoning: OpenRouter DeepSeek R1
      - offline: Ollama phi3.5 (local)
    """
    if task_type == "weekly":
        return await _call_gemini(prompt, system)
    elif task_type == "nightly":
        return await _call_cerebras(prompt, system)
    elif task_type == "reasoning":
        return await _call_openrouter(prompt, system)
    elif task_type == "offline":
        return await _call_ollama(prompt, system)
    else:
        try:
            return await _call_groq(prompt, system)
        except Exception:
            return await _call_cerebras(prompt, system)


async def _call_groq(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": messages}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_gemini(prompt: str, system: str = "") -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": full_prompt}]}]}
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_cerebras(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_KEY}"},
            json={"model": "llama-3.3-70b", "messages": messages}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_openrouter(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={"model": "deepseek/deepseek-r1:free", "messages": messages}
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_ollama(prompt: str, system: str = "") -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "phi3.5", "prompt": full_prompt, "stream": False}
        )
        r.raise_for_status()
        return r.json()["response"]
