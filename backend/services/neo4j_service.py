import os
import asyncio
import logging

log = logging.getLogger("neo4j-service")

NEO4J_URL = os.getenv("NEO4J_URL", "bolt://neo4j:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

_driver = None
_lock = asyncio.Lock()

async def get_driver():
    global _driver
    if _driver is not None:
        return _driver

    async with _lock:
        if _driver is None:
            from neo4j import AsyncGraphDatabase
            log.info(f"Initializing Neo4j driver for {NEO4J_URL}")
            _driver = AsyncGraphDatabase.driver(NEO4J_URL, auth=("neo4j", NEO4J_PASSWORD))
        return _driver

async def close_driver():
    global _driver
    async with _lock:
        if _driver is not None:
            log.info("Closing Neo4j driver")
            await _driver.close()
            _driver = None
