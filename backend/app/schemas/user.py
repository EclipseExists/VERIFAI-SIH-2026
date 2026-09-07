"""
VERIFAI — User & Auth Schemas
===============================

Pydantic models for user registration, login, and JWT tokens.

HOW JWT AUTH WORKS (simplified):
1. Officer sends email + password to POST /api/v1/auth/login
2. Backend verifies credentials against the users table
3. Backend returns a JWT token (a signed, time-limited string)
4. Officer's browser sends this token in every subsequent request
5. Backend verifies the token signature and extracts the user ID + role
6. If the token is expired or invalid, the request is rejected

WHY JWT:
- Stateless: no server-side session storage needed
- The token itself contains the user ID and role
- Easy to implement with python-jose library
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Data needed to register a new user (admin action)."""
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: str
    role: Literal["officer", "admin"] = "officer"


class UserOut(BaseModel):
    """User data returned by the API (never includes password!)."""
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT token returned after successful login."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Data encoded inside the JWT token.

    'sub' = subject = the user's UUID
    'role' = officer or admin
    'exp' = expiry timestamp (Unix epoch)
    """
    sub: UUID
    role: str
    exp: int

