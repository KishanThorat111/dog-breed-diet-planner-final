"""
Auth router — register, login, and me endpoints.
Uses HS256 JWT tokens. No external auth service required.
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
)
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
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str | None = None
    is_admin: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


def _validate_password(password: str) -> None:
    """Enforce minimum production password requirements."""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must include at least one uppercase letter",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must include at least one lowercase letter",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must include at least one number",
        )


# -- Endpoints ----------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Create a new account and return an access token."""
    logger.info(
        "auth.register.in req_id=%s origin=%s email=%s",
        getattr(request.state, "request_id", ""),
        request.headers.get("origin", ""),
        body.email,
    )
    _validate_password(body.password)

    existing = await user_service.get_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = await user_service.create_user(db, body.email, body.password, body.full_name)
    token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    logger.info("New user registered: %s", user.email)

    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password and return an access token."""
    logger.info(
        "auth.login.in req_id=%s origin=%s email=%s",
        getattr(request.state, "request_id", ""),
        request.headers.get("origin", ""),
        body.email,
    )
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
    refresh_token = create_refresh_token(user.id, user.email)
    logger.info("User logged in: %s", user.email)

    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a fresh access token from a valid refresh token."""
    logger.info(
        "auth.refresh.in req_id=%s origin=%s",
        getattr(request.state, "request_id", ""),
        request.headers.get("origin", ""),
    )

    payload = decode_refresh_token(body.refresh_token)
    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    user = await user_service.get_by_email(db, str(email))
    if not user or str(user.id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token(user.id, user.email)
    new_refresh_token = create_refresh_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
    )


@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user and subscription usage summary."""
    from sqlalchemy import select

    from app.models.subscription import Subscription
    from app.services.quota_service import quota_service

    sub = (
        await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    ).scalar_one_or_none()
    if sub is None:
        sub = await quota_service.ensure_subscription(db, current_user.id)

    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "is_admin": current_user.is_admin,
        "subscription": {
            "plan": sub.plan,
            "status": sub.status,
            "credits_remaining": sub.credits_remaining,
            "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        },
    }
