import asyncio, httpx
from pathlib import Path

async def index_vault():
    files = list(Path('/vault').glob('**/*.md'))
    print(f'Indexing {len(files)} files into LightRAG...')
    for i, f in enumerate(files):
        content = f.read_text(encoding='utf-8', errors='ignore')
        if len(content.strip()) < 20: continue
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post('http://localhost:9621/documents/text',
                    json={'text': content, 'description': f.stem})
                print(f'[{i+1}/{len(files)}] {f.name}: {r.status_code}')
        except Exception as e:
            print(f'[{i+1}/{len(files)}] {f.name}: ERROR - {e}')
        await asyncio.sleep(0.5)

asyncio.run(index_vault())
