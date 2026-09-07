"""
VERIFAI — Authentication Endpoints
=====================================

POST /api/v1/auth/login   → officer logs in, gets a JWT token
POST /api/v1/auth/register → admin creates a new user account
GET  /api/v1/auth/me      → officer gets their own profile

HOW JWT AUTHENTICATION WORKS (simple version):
1. Officer sends email + password to /login
2. Backend verifies password against hashed password in DB
3. Backend returns a signed JWT token (like a digital ID card)
4. Officer sends this token in every future request in the Authorization header
5. Backend verifies the token to know WHO is making the request

The token contains: user ID, email, role, expiry time
It's cryptographically signed so it can't be forged.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserOut

router = APIRouter()
settings = get_settings()

# ── Password hashing using bcrypt ──────────────────────────────────
# bcrypt is a one-way hash — you can NEVER reverse it to get the password.
# This is what "hashing" means. We store the hash, not the password.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def _hash_password(password: str) -> str:
    """Turn a plain password into a bcrypt hash."""
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    """Check if a plain password matches its stored hash."""
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: UUID, email: str, role: str) -> str:
    """
    Create a JWT token for a logged-in user.
    The token expires after ACCESS_TOKEN_EXPIRE_MINUTES minutes.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),   # "subject" — who this token is for
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


@router.post(
    "/login",
    response_model=Token,
    summary="Officer login",
    description="Exchange email + password for a JWT access token.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> Token:
    """
    Login endpoint.

    Uses OAuth2PasswordRequestForm which reads username + password from
    form fields (not JSON). This matches standard OAuth2 conventions and
    lets the Swagger UI 'Authorize' button work directly.

    Note: 'username' in the form is our user's email address.
    """
    # Find the user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Validate credentials — same error message for wrong email OR wrong password
    # (prevents attackers from knowing which one was wrong)
    if not user or not _verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact an administrator.",
        )

    # Audit log the login
    ip = request.client.host if request and request.client else None
    db.add(AuditLog(
        user_id=user.id,
        action="user_login",
        details=f"Login for {user.email}",
        ip_address=ip,
    ))
    await db.commit()

    token = _create_access_token(user.id, user.email, user.role)
    return Token(access_token=token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (admin only)",
    description="Admin creates officer or admin accounts. No self-registration.",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Create a new user account.

    In a real deployment, this would require an admin JWT token.
    For the hackathon prototype, it's open (TODO: add admin-only guard).
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {user_in.email} is already registered.",
        )

    new_user = User(
        email=user_in.email,
        hashed_password=_hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
    )
    db.add(new_user)

    db.add(AuditLog(
        user_id=None,
        action="user_created",
        details=f"New user: {user_in.email} role={user_in.role}",
    ))

    await db.commit()
    await db.refresh(new_user)
    return UserOut.model_validate(new_user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get my profile",
)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """
    Returns the profile of the currently logged-in user.
    For now returns the seed officer.
    TODO: Extract user from JWT token.
    """
    seed_id = UUID("00000000-0000-0000-0000-000000000001")
    user = await db.get(User, seed_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
