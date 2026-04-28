import os
import hashlib
import logging
import asyncpg
from datetime import datetime

log = logging.getLogger("brain.collector")
DATABASE_URL = os.getenv("DATABASE_URL")
VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
VAULT_SCAN_DIRS = os.getenv("VAULT_SCAN_DIRS", "01-Journal,03-AI-Chats,04-Resources,05-Content").split(",")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

async def run_nightly_crawl():
    """Triggered by APScheduler and on-demand via API."""
    log.info("Starting vault crawl...")
    conn = await get_conn()
    files_processed = 0
    errors = 0
    
    try:
        from skills.locus.brain.chunker import process_file_into_chunks
        
        for scan_dir in VAULT_SCAN_DIRS:
            dir_path = os.path.join(VAULT_PATH, scan_dir.strip())
            if not os.path.exists(dir_path):
                log.warning(f"Scan directory not found: {dir_path}")
                continue
                
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if not file.endswith(".md"):
                        continue
                        
                    full_path = os.path.join(root, file)
                    # Relative path from vault root
                    rel_path = os.path.relpath(full_path, VAULT_PATH)
                    
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        file_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
                        
                        # Check index state
                        row = await conn.fetchrow(
                            "SELECT file_hash FROM vault_index_state WHERE file_path = $1", 
                            rel_path
                        )
                        
                        if row and row["file_hash"] == file_hash:
                            # Unchanged
                            continue
                            
                        # File is new or changed -> pass to Chunker
                        chunk_count = await process_file_into_chunks(rel_path, content, conn)
                        
                        # Update index state
                        await conn.execute("""
                            INSERT INTO vault_index_state (file_path, file_hash, last_indexed_at, chunk_count)
                            VALUES ($1, $2, NOW(), $3)
                            ON CONFLICT (file_path) DO UPDATE SET
                                file_hash = EXCLUDED.file_hash,
                                last_indexed_at = NOW(),
                                chunk_count = EXCLUDED.chunk_count
                        """, rel_path, file_hash, chunk_count)
                        
                        files_processed += 1
                        
                    except Exception as e:
                        errors += 1
                        log.error(f"Error processing file {rel_path}: {str(e)}")
                        await conn.execute("""
                            INSERT INTO brain_errors (subsystem, file_path, error_msg, severity)
                            VALUES ($1, $2, $3, $4)
                        """, 'collector', rel_path, str(e), 2)
                        
        # Log to behavioral_events
        await conn.execute("""
            INSERT INTO behavioral_events (user_id, event_type, data)
            VALUES ($1, $2, $3)
        """, 'shivam', 'vault_crawl', f'{{"files_processed": {files_processed}, "errors": {errors}}}')
        
    finally:
        await conn.close()
        
    log.info(f"Vault crawl completed. Processed: {files_processed}, Errors: {errors}")
    return {"files_processed": files_processed, "errors": errors}
