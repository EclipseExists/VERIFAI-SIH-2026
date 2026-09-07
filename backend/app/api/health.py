"""
VERIFAI — Health Check Endpoint
=================================

This is the FIRST endpoint you should test. If this works,
FastAPI + PostgreSQL are correctly wired together.

WHY HEALTH CHECKS EXIST:
- Quick way to verify the server is running and the DB is reachable
- Used by Docker, load balancers, and monitoring tools
- During development: "did I break something?" → check /api/v1/health/
- During the demo: prove to judges the system is live

HOW IT CONNECTS TO VERIFAI:
- This is mounted at GET /api/v1/health/
- It tests the database connection by running a simple query
- If the database is down, it returns database="disconnected"
  but still returns 200 (the API itself is healthy, just the DB isn't)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description="Verify the API is running and the database is reachable.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Returns the API status, version, and database connectivity.

    This endpoint:
    1. Confirms FastAPI is serving requests
    2. Runs 'SELECT 1' to test the PostgreSQL connection
    3. Reports the result
    """
    # Test database connectivity with the simplest possible query
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        database=db_status,
    )

