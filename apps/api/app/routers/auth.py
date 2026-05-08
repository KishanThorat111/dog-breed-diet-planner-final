"""
Auth router — register, login, and me endpoints.
Uses HS256 JWT tokens. No external auth service required.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import create_access_token, get_current_user
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


# -- Request/Response schemas ------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str | None = None
    is_admin: bool = False


# -- Endpoints ----------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Create a new account and return an access token."""
    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    existing = await user_service.get_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = await user_service.create_user(db, body.email, body.password, body.full_name)
    token = create_access_token(user.id, user.email)
    logger.info("New user registered: %s", user.email)

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate with email + password and return an access token."""
    user = await user_service.authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(user.id, user.email)
    logger.info("User logged in: %s", user.email)

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user."""
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "is_admin": current_user.is_admin,
    }
