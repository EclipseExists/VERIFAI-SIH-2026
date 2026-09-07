"""
VERIFAI — Application Configuration
=====================================

This file centralizes ALL configuration for the VERIFAI backend.

WHY THIS FILE EXISTS:
- Keeps secrets (DB password, JWT key) out of source code
- Reads from environment variables or a .env file
- One place to change settings instead of hunting through 20 files
- pydantic-settings validates types automatically (e.g., ensures port is an int)

HOW IT CONNECTS TO VERIFAI:
- Every other module imports `get_settings()` to access config
- Database URL, JWT secrets, file paths — all flow from here
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic-settings reads from:
    1. Environment variables (highest priority)
    2. .env file in the backend/ directory
    3. Default values defined here (lowest priority)

    This means you can override any setting by setting an env var,
    without touching code.
    """

    # ── Project Metadata ──────────────────────────────────────────
    PROJECT_NAME: str = "VERIFAI"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────
    # postgresql+asyncpg:// tells SQLAlchemy to use the async PostgreSQL driver
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = "postgresql+asyncpg://verifai:verifai_dev@localhost:5432/verifai_db"

    # ── Authentication ────────────────────────────────────────────
    # Used to sign JWT tokens. MUST be changed in production.
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    # How long a login session lasts before the officer must re-authenticate
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── File Storage ──────────────────────────────────────────────
    # Where uploaded document images are saved on disk
    UPLOAD_DIR: str = "uploads"

    # ── Pydantic-Settings Config ──────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",         # Load from .env file in working directory
        case_sensitive=True,     # ENV_VAR must match field name exactly
        extra="ignore",          # Don't crash if .env has extra variables
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached singleton of Settings.

    WHY CACHED:
    - Settings don't change at runtime
    - Reading .env file on every request would be wasteful
    - lru_cache ensures we parse the config exactly once
    """
    return Settings()

