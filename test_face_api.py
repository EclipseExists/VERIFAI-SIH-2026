import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # We need a valid case_id and document_id... 
        pass
