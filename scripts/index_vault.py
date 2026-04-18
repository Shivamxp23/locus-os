import asyncio, httpx, sys
from pathlib import Path

async def index_vault():
    files = list(Path('/vault').glob('**/*.md'))
    print(f'Indexing {len(files)} files into LightRAG...', flush=True)
    success = 0
    skipped = 0
    errors = 0
    for i, f in enumerate(files):
        content = f.read_text(encoding='utf-8', errors='ignore')
        if len(content.strip()) < 20:
            skipped += 1
            continue
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post('http://localhost:9621/documents/text',
                    json={'text': content, 'description': f.stem})
                if r.status_code == 200:
                    success += 1
                else:
                    errors += 1
                print(f'[{i+1}/{len(files)}] {f.name}: {r.status_code}', flush=True)
        except Exception as e:
            errors += 1
            print(f'[{i+1}/{len(files)}] {f.name}: ERROR - {e}', flush=True)
        await asyncio.sleep(0.5)
    print(f'Indexing complete! Success: {success}, Skipped: {skipped}, Errors: {errors}', flush=True)

asyncio.run(index_vault())
