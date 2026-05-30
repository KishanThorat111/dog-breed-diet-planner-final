from __future__ import annotations

import asyncio
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserPublic
from app.services.user_service import user_service

router = APIRouter(dependencies=[Depends(require_admin)])


# ============================================================================
# Users
# ============================================================================

@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    users, total = await user_service.list_users(db, page, page_size)
    return PaginatedResponse(
        items=[UserPublic.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """High-level platform statistics for admin dashboard."""
    from sqlalchemy import func, select
    from app.models.pet import Pet
    from app.models.prediction import AIPrediction
    from app.models.diet_plan import DietPlan

    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )).scalar_one()

    pet_count = (await db.execute(
        select(func.count()).select_from(Pet).where(Pet.deleted_at.is_(None))
    )).scalar_one()

    prediction_count = (await db.execute(
        select(func.count()).select_from(AIPrediction)
    )).scalar_one()

    diet_plan_count = (await db.execute(
        select(func.count()).select_from(DietPlan)
    )).scalar_one()

    return {
        "users": user_count,
        "pets": pet_count,
        "predictions": prediction_count,
        "diet_plans": diet_plan_count,
    }


# ============================================================================
# AI Provider Management
# API keys are NEVER returned — admin sees only provider names + status.
# ============================================================================

class AIConfigUpdate(BaseModel):
    active_provider: str | None = None
    active_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    enabled: bool | None = None


def _provider_status_summary() -> list[dict]:
    """Return per-provider status — configured/not-configured only, NO keys."""
    from app.ai.factory import AIProviderFactory
    rows = []
    for name in AIProviderFactory.available_providers():
        provider = AIProviderFactory.get(name)
        rows.append({
            "name": name,
            "configured": provider.is_configured,
        })
    return rows


@router.get("/ai/config")
async def get_ai_config() -> dict:
    """
    Return current AI runtime config.
    Includes provider status but NEVER includes API keys.
    """
    from app.ai.config import get_ai_config as _get_cfg
    cfg = _get_cfg()
    return {
        **cfg.as_dict(),
        "providers": _provider_status_summary(),
    }


@router.put("/ai/config")
async def update_ai_config(body: AIConfigUpdate) -> dict:
    """
    Update active AI provider/model and generation parameters at runtime.
    Changes reset on process restart; update Railway env vars for persistence.
    """
    from app.ai.config import update_ai_config as _update
    from app.ai.factory import AIProviderFactory

    updates = body.model_dump(exclude_none=True)

    # Validate provider names
    if "active_provider" in updates:
        available = AIProviderFactory.available_providers()
        if updates["active_provider"] not in available:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown provider '{updates['active_provider']}'. "
                       f"Available: {available}",
            )

    updated = _update(**updates)
    return {
        **updated.as_dict(),
        "providers": _provider_status_summary(),
    }


@router.get("/ai/health")
async def check_ai_health() -> dict:
    """
    Run a lightweight health check against every configured provider.
    Results show latency in ms; never show API keys.
    """
    from app.ai.factory import AIProviderFactory

    async def _check(name: str) -> dict:
        provider = AIProviderFactory.get(name)
        if not provider.is_configured:
            return {"provider": name, "configured": False, "healthy": None, "latency_ms": None}
        try:
            ok, latency = await asyncio.wait_for(provider.health_check(), timeout=10)
            return {"provider": name, "configured": True, "healthy": ok, "latency_ms": latency}
        except Exception as exc:
            return {"provider": name, "configured": True, "healthy": False, "latency_ms": None, "error": str(exc)}

    results = await asyncio.gather(
        *[_check(name) for name in AIProviderFactory.available_providers()]
    )
    return {"results": list(results)}


class AITestRequest(BaseModel):
    provider: str
    prompt: str = "What is a Labrador Retriever's typical energy requirement?"


@router.post("/ai/test")
async def test_ai_provider(body: AITestRequest) -> dict:
    """
    Send a test prompt to a specific provider.
    Returns the response text and latency.
    Rate-limited to admin users only.
    """
    from app.ai.base import AIRequest
    from app.ai.factory import AIProviderFactory

    available = AIProviderFactory.available_providers()
    if body.provider not in available:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown provider '{body.provider}'. Available: {available}",
        )

    provider = AIProviderFactory.get(body.provider)
    if not provider.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider '{body.provider}' is not configured (missing API key)",
        )

    # Sanitize the test prompt — admin-only but still apply basic limits
    safe_prompt = body.prompt[:500]

    try:
        response = await provider.complete(
            AIRequest(
                prompt=safe_prompt,
                max_tokens=256,
                temperature=0.5,
                timeout_seconds=15,
                json_mode=False,
                metadata={"caller": "admin_test"},
            )
        )
        return {
            "ok": True,
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "response_preview": response.content[:300],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider test failed: {exc}",
        )
