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


@router.get("/analytics")
async def get_analytics(db: AsyncSession = Depends(get_db)) -> dict:
    """Extended analytics for admin dashboards."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from app.models.ai_usage import AIUsage
    from app.models.pet import Pet
    from app.models.pet_expense import PetExpense
    from app.models.pet_health_record import PetHealthRecord
    from app.models.pet_medication_schedule import PetMedicationSchedule
    from app.models.pet_vaccination import PetVaccination
    from app.models.pet_weight_log import PetWeightLog

    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)
    growth_start = now - timedelta(days=190)

    def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
        idx = (year * 12 + (month - 1)) + delta
        return idx // 12, idx % 12 + 1

    labels: list[str] = []
    for offset in range(-5, 1):
        y, m = _shift_month(now.year, now.month, offset)
        labels.append(f"{y:04d}-{m:02d}")

    users_rows = (
        await db.execute(
            select(User.created_at)
            .where(User.deleted_at.is_(None), User.created_at >= growth_start)
            .order_by(User.created_at.asc())
        )
    ).scalars().all()
    users_growth = {label: 0 for label in labels}
    for created_at in users_rows:
        key = f"{created_at.year:04d}-{created_at.month:02d}"
        if key in users_growth:
            users_growth[key] += 1

    pets_rows = (
        await db.execute(
            select(Pet.created_at)
            .where(Pet.deleted_at.is_(None), Pet.created_at >= growth_start)
            .order_by(Pet.created_at.asc())
        )
    ).scalars().all()
    pets_growth = {label: 0 for label in labels}
    for created_at in pets_rows:
        key = f"{created_at.year:04d}-{created_at.month:02d}"
        if key in pets_growth:
            pets_growth[key] += 1

    upcoming_vaccinations = (
        await db.execute(
            select(func.count())
            .select_from(PetVaccination)
            .where(
                PetVaccination.is_completed.is_(False),
                PetVaccination.due_on >= today,
                PetVaccination.due_on <= today + timedelta(days=30),
            )
        )
    ).scalar_one()

    overdue_vaccinations = (
        await db.execute(
            select(func.count())
            .select_from(PetVaccination)
            .where(PetVaccination.is_completed.is_(False), PetVaccination.due_on < today)
        )
    ).scalar_one()

    active_medications = (
        await db.execute(
            select(func.count())
            .select_from(PetMedicationSchedule)
            .where(PetMedicationSchedule.is_active.is_(True))
        )
    ).scalar_one()

    health_records = (
        await db.execute(select(func.count()).select_from(PetHealthRecord))
    ).scalar_one()

    weight_logs = (
        await db.execute(select(func.count()).select_from(PetWeightLog))
    ).scalar_one()

    expense_total_raw = (
        await db.execute(
            select(func.coalesce(func.sum(PetExpense.amount), 0)).where(PetExpense.expense_on >= month_start)
        )
    ).scalar_one()

    usage_7d = (
        await db.execute(
            select(
                func.count().label("events"),
                func.coalesce(func.sum(AIUsage.prompt_tokens + AIUsage.completion_tokens), 0).label("tokens"),
            ).where(AIUsage.created_at >= now - timedelta(days=7))
        )
    ).one()

    return {
        "user_growth": [{"month": label, "count": users_growth[label]} for label in labels],
        "pet_growth": [{"month": label, "count": pets_growth[label]} for label in labels],
        "wellness": {
            "upcoming_vaccinations": upcoming_vaccinations,
            "overdue_vaccinations": overdue_vaccinations,
            "active_medications": active_medications,
            "health_records": health_records,
            "weight_logs": weight_logs,
            "monthly_expense_total": float(expense_total_raw or 0),
        },
        "ai_usage_7d": {
            "events": usage_7d.events,
            "tokens": int(usage_7d.tokens or 0),
        },
    }


# ============================================================================
# AI Provider Management
# API keys are NEVER returned — admin sees only provider names + status.
# ============================================================================

class AIConfigUpdate(BaseModel):
    active_provider: str | None = None
    active_model: str | None = None
    fallback_models: list[str] | None = None
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


_DEPRECATED_GEMINI_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
}


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

    # Validate Gemini model deprecations and normalize fallback list.
    active_model = updates.get("active_model")
    if isinstance(active_model, str) and active_model in _DEPRECATED_GEMINI_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Model '{active_model}' is shut down. "
                "Use 'gemini-2.5-flash' as primary and 'gemini-2.5-flash-lite' as fallback."
            ),
        )

    if "fallback_models" in updates:
        raw_fallbacks = updates.get("fallback_models") or []
        normalized: list[str] = []
        seen: set[str] = set()
        primary = updates.get("active_model")
        for model in raw_fallbacks:
            if model in _DEPRECATED_GEMINI_MODELS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Fallback model '{model}' is shut down. "
                        "Use 'gemini-2.5-flash-lite'."
                    ),
                )
            if model and model != primary and model not in seen:
                seen.add(model)
                normalized.append(model)
        updates["fallback_models"] = normalized

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


@router.get("/ai/usage")
async def list_ai_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List AI usage events for admin.

    Paginated results ordered by newest first.
    """
    from sqlalchemy import select, func
    from app.models.ai_usage import AIUsage

    base = select(AIUsage)
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()
    result = await db.execute(base.order_by(AIUsage.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    items = [dict(
        id=str(r.id),
        user_id=str(r.user_id) if r.user_id else None,
        provider=r.provider,
        model=r.model,
        prompt_tokens=r.prompt_tokens,
        completion_tokens=r.completion_tokens,
        caller=r.caller,
        reference_type=r.reference_type,
        reference_id=str(r.reference_id) if r.reference_id else None,
        created_at=r.created_at.isoformat() if r.created_at else None,
    ) for r in result.scalars().all()]

    pages = (total + page_size - 1) // page_size if total else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


class CreditTopup(BaseModel):
    user_id: str
    credits: int


@router.post("/credits/topup")
async def topup_credits(body: CreditTopup, db: AsyncSession = Depends(get_db)) -> dict:
    """Add credits to a user's subscription (admin only)."""
    from sqlalchemy import select
    from app.models.user import User
    from app.models.subscription import Subscription
    import uuid as _uuid

    try:
        user_id = _uuid.UUID(body.user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user_id")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sub = (await db.execute(select(Subscription).where(Subscription.user_id == user_id))).scalar_one_or_none()
    if not sub:
        # create default subscription row
        sub = Subscription(user_id=user_id, plan="free", credits_remaining=body.credits)
        db.add(sub)
        await db.commit()
        return {"ok": True, "credits": sub.credits_remaining}

    sub.credits_remaining = (sub.credits_remaining or 0) + body.credits
    await db.commit()
    return {"ok": True, "credits": sub.credits_remaining}


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
