"""
VERIFAI — Async Database Session Management
=============================================

This file sets up the connection between FastAPI and PostgreSQL.

WHY ASYNC:
- FastAPI is an async framework — it handles many requests concurrently
- If we used synchronous database calls, one slow query would block
  ALL other requests (bad for a checkpoint system handling multiple cases)
- asyncpg is one of the fastest PostgreSQL drivers available

HOW DEPENDENCY INJECTION WORKS:
- FastAPI's Depends() system automatically calls get_db() for each request
- The request gets its own database session
- When the request ends, the session is automatically closed
- This prevents connection leaks (a common beginner mistake)

HOW IT CONNECTS TO VERIFAI:
- Every API endpoint that touches the database uses: db: AsyncSession = Depends(get_db)
- The engine is also used in main.py to auto-create tables on startup
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# ── Create the async database engine ──────────────────────────────
# The engine manages a pool of database connections.
# echo=False means SQL queries are NOT printed to console
# (set echo=True temporarily when debugging SQL issues)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # Pool settings for development — PostgreSQL allows 100 connections
    # by default. We use a small pool since this is a prototype.
    pool_size=5,
    max_overflow=10,
)

# ── Session Factory ───────────────────────────────────────────────
# This creates new database sessions.
# expire_on_commit=False means we can still access object attributes
# after committing (important for returning data in API responses).
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in an endpoint:
        @router.get("/cases")
        async def list_cases(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed when the request finishes,
    even if an error occurs (thanks to the try/finally pattern).
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

