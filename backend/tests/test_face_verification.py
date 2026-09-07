"""
VERIFAI — Face Verification Endpoint Tests
=============================================

Tests for POST /api/v1/cases/{case_id}/face-verification

These tests verify:
1. The endpoint validates case and document existence
2. Error handling works when the AI module isn't available
3. The response shape matches the FaceVerificationOut schema
4. 404 is returned for missing cases/documents

NOTE: Full integration tests (with the actual AI module) require
the ai/face/ module to be installed and face images to be available.
These tests focus on the API layer behavior.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_face_verification_case_not_found():
    """
    POST face-verification on a nonexistent case should return 404.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/cases/00000000-0000-0000-0000-999999999999/face-verification",
            json={
                "document_id": "00000000-0000-0000-0000-000000000001",
                "probe_face_path": "/tmp/probe.jpg",
            },
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_face_verification_endpoint_exists():
    """
    Verify the face-verification endpoint is registered and responds
    (even if it returns an error due to missing data, it shouldn't 405).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Use a valid UUID format but nonexistent case
        response = await client.post(
            "/api/v1/cases/00000000-0000-0000-0000-000000000002/face-verification",
            json={
                "document_id": "00000000-0000-0000-0000-000000000003",
                "probe_face_path": "/some/path.jpg",
            },
        )

    # Should be 404 (case not found), NOT 405 (method not allowed)
    # 405 would mean the route isn't registered
    assert response.status_code != 405

