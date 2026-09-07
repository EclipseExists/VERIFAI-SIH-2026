"""
VERIFAI — FastAPI Application Entry Point
===========================================

This is the file that starts everything.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.router import api_router
from app.db.session import engine, async_session_factory

# ── Import ALL models so SQLAlchemy knows to create their tables ───
from app.models.base import Base
from app.models.user import User              # noqa: F401
from app.models.case import Case, Document   # noqa: F401
from app.models.audit import AuditLog        # noqa: F401
from app.models.face_verification import FaceVerification  # noqa: F401
from app.models.ocr_result import OcrResult  # noqa: F401
from app.models.mrz_result import MrzResult  # noqa: F401
from app.models.forensics_result import ForensicsResult  # noqa: F401
from app.models.risk_assessment import RiskAssessment, RiskSignal  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + seed dev officer. Shutdown: close DB."""
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")

    # Create all tables (safe — won't drop existing data)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created/verified")

    # Seed the placeholder officer account for development
    import uuid
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SEED_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

    async with async_session_factory() as session:
        existing = await session.get(User, SEED_ID)
        if not existing:
            seed_officer = User(
                id=SEED_ID,
                email="officer@verifai.dev",
                hashed_password=pwd_context.hash("officer123"),
                full_name="Demo Officer",
                role="officer",
                is_active=True,
            )
            session.add(seed_officer)
            await session.commit()
            print("✅ Seed officer created — email: officer@verifai.dev / password: officer123")
        else:
            print("ℹ️  Seed officer already exists")

    yield  # App runs here

    print(f"👋 Shutting down {settings.PROJECT_NAME}")
    await engine.dispose()


# ── Create the FastAPI application ────────────────────────────────
app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description=(
        "AI-Powered Fake Identity & Document Risk Screening — "
        "Decision Support for Checkpoint Officers. "
        "All final decisions are made by human officers."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── CORS — allow React frontend on any localhost port ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount all API routes under /api/v1 ────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", summary="Root", tags=["root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health/",
        "description": (
            "VERIFAI — AI-powered document risk screening. "
            "All decisions are made by human officers."
        ),
    }
