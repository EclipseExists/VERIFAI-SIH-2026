"""
VERIFAI — Health & Root Endpoint Tests
========================================

HOW FASTAPI TESTING WORKS:
- We use httpx.AsyncClient to send HTTP requests to the FastAPI app
- No running server needed! httpx talks directly to the ASGI app in-process
- This is fast, isolated, and doesn't require a database for basic tests

WHAT THESE TESTS VERIFY:
- The FastAPI app starts without errors
- The root endpoint returns the expected welcome message
- The /docs Swagger UI is accessible

WHY TEST EVEN SIMPLE THINGS:
- If you accidentally break an import, these tests catch it immediately
- They take <1 second to run
- They prove to judges that you have a testing strategy
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """
    GET / should return 200 and contain 'VERIFAI' in the response.

    This is the smoke test — if this fails, something fundamental is broken.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "VERIFAI" in data["message"]
    assert "docs" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_docs_available():
    """
    GET /docs should return 200 (Swagger UI is accessible).

    The Swagger UI at /docs is where teammates and judges can
    interactively test every endpoint.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/docs")

    assert response.status_code == 200

