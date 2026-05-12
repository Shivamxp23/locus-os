import os
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter
import asyncpg

log = logging.getLogger("brain.reader")
VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

def strip_yaml_frontmatter(content: str) -> str:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return content

class ReadRequest(BaseModel):
    file_path: str

class ReadResponse(BaseModel):
    found: bool
    content: Optional[str]
    word_count: int = 0
    truncated: bool = False

async def read_vault_file(file_path: str) -> ReadResponse:
    full_path = os.path.join(VAULT_PATH, file_path)
    
    # Secure path traversal check
    if not os.path.normpath(full_path).startswith(os.path.normpath(VAULT_PATH)):
        return ReadResponse(found=False, content=None)
        
    if not os.path.isfile(full_path):
        return ReadResponse(found=False, content=None)
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            
        content = strip_yaml_frontmatter(raw_content)
        words = content.split()
        word_count = len(words)
        truncated = False
        
        if word_count > 8000:
            content = " ".join(words[:8000])
            word_count = 8000
            truncated = True
            
        # Log to behavioral_events
        conn = await get_conn()
        try:
            await conn.execute("""
                INSERT INTO behavioral_events (user_id, event_type, data)
                VALUES ($1, $2, $3)
            """, 'shivam', 'file_read', f'{{"file_path": "{file_path}"}}')
        finally:
            await conn.close()
            
        return ReadResponse(
            found=True,
            content=content,
            word_count=word_count,
            truncated=truncated
        )
    except Exception as e:
        log.error(f"Error reading file {file_path}: {e}")
        return ReadResponse(found=False, content=None)
