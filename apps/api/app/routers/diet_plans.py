from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.common import APIBaseModel, PaginatedResponse
from app.schemas.diet_plan import (
    DietPlanPublic,
    FoodRecommendation,
    FeedingScheduleItem,
)
from app.services.diet_engine import diet_engine
from app.middleware.auth import ANONYMOUS_USER_ID, get_optional_user

router = APIRouter()


def _derive_life_stage(age_months: int) -> str:
    if age_months < 12:
        return "puppy"
    if age_months >= 84:
        return "senior"
    return "adult"


def _breed_to_pet_name(breed: str | None) -> str:
    if not breed:
        return "My Dog"
    name = breed.replace("_", " ").strip().title()
    return name or "My Dog"


def _safe_pet_name(name: str | None, fallback_breed: str | None) -> str:
    """Normalize user/AI-derived pet names to a DB-safe value."""
    raw = (name or "").strip()
    if not raw:
        raw = _breed_to_pet_name(fallback_breed)

    # Collapse excessive whitespace and enforce schema max length.
    normalized = " ".join(raw.split())
    if len(normalized) > 100:
        normalized = normalized[:100].rstrip()

    return normalized or "My Dog"


class AnonDietPlanRequest(APIBaseModel):
    """Diet-plan request. Authenticated requests are always persisted."""
    pet_id: uuid.UUID | None = None
    prediction_id: uuid.UUID | None = None
    pet_name: str | None = None
    breed: str | None = None
    age_months: Annotated[int | None, Field(ge=0, le=360)] = None
    weight_kg: Annotated[Decimal | None, Field(ge=Decimal("0.1"), le=Decimal("200"))] = None
    activity_level: str | None = None
    is_neutered: bool = True
    sex: str = "male"
    allergies: list[str] = []
    health_conditions: list[str] = []


@router.post("/generate", response_model=DietPlanPublic, status_code=status.HTTP_201_CREATED)
async def generate_diet_plan(
    request: AnonDietPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> DietPlanPublic:
    """Generate a diet plan. Authenticated requests are persisted for reports/download."""
    breed = request.breed or "unknown"
    age_months = request.age_months if request.age_months is not None else 24
    weight_kg = float(request.weight_kg) if request.weight_kg is not None else 10.0
    activity_level = request.activity_level or "moderate"

    if current_user:
        from app.services.diet_service import diet_service
        from app.services.pet_service import pet_service
        from app.schemas.diet_plan import DietPlanGenerateRequest as SchemaReq
        from app.schemas.pet import PetCreate
        from app.models.pet import Pet as PetModel
        from app.models.prediction import AIPrediction

        prediction: AIPrediction | None = None
        if request.prediction_id:
            prediction_res = await db.execute(
                select(AIPrediction).where(
                    AIPrediction.id == request.prediction_id,
                    AIPrediction.user_id == current_user.id,
                )
            )
            prediction = prediction_res.scalar_one_or_none()
            if not prediction:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

        resolved_breed = request.breed or (prediction.top_breed if prediction else None) or "mixed_breed"
        resolved_age_months = request.age_months if request.age_months is not None else 24
        resolved_weight = float(request.weight_kg) if request.weight_kg is not None else 10.0
        resolved_activity = request.activity_level or "moderate"

        if request.pet_id:
            # load and validate pet ownership
            pet_res = await db.execute(
                select(PetModel).where(
                    PetModel.id == request.pet_id,
                    PetModel.user_id == current_user.id,
                )
            )
            pet = pet_res.scalar_one_or_none()
            if not pet:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
        else:
            auto_pet_name = _safe_pet_name(request.pet_name, resolved_breed)
            try:
                pet_payload = PetCreate(
                    name=auto_pet_name,
                    breed=resolved_breed,
                    age_months=resolved_age_months,
                    weight_kg=Decimal(str(resolved_weight)),
                    sex=request.sex,
                    is_neutered=request.is_neutered,
                    life_stage=_derive_life_stage(resolved_age_months),
                    activity_level=resolved_activity,
                    allergies=request.allergies,
                    health_conditions=request.health_conditions,
                    notes=None,
                )
            except ValidationError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid diet generation inputs: {exc.errors()[0].get('msg', 'validation failed')}",
                ) from exc
            pet = await pet_service.create(db, current_user.id, pet_payload)

        schema_req = SchemaReq(
            pet_id=pet.id,
            prediction_id=request.prediction_id,
            breed=request.breed or (prediction.top_breed if prediction else None),
            age_months=request.age_months,
            weight_kg=request.weight_kg,
            activity_level=request.activity_level,
        )

        plan = await diet_service.generate_for_pet(db, current_user.id, schema_req, pet)
        return DietPlanPublic.model_validate(plan)

    # Anonymous or no-pet fallback: in-memory generation (no persistence)
    result = diet_engine.generate(
        breed=breed,
        age_months=age_months,
        weight_kg=weight_kg,
        activity_level=activity_level,
        is_neutered=request.is_neutered,
        sex=request.sex,
        allergies=request.allergies,
        health_conditions=request.health_conditions,
    )

    now = datetime.now(timezone.utc)
    return DietPlanPublic(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=ANONYMOUS_USER_ID,
        prediction_id=None,
        breed=result.breed,
        age_months=result.age_months,
        weight_kg=Decimal(str(result.weight_kg)),
        activity_level=result.activity_level,
        daily_calories=result.daily_calories,
        protein_g=Decimal(str(result.protein_g)),
        fat_g=Decimal(str(result.fat_g)),
        carbs_g=Decimal(str(result.carbs_g)),
        meals_per_day=result.meals_per_day,
        food_recommendations=[FoodRecommendation(**f) for f in result.food_recommendations],
        foods_to_avoid=result.foods_to_avoid,
        supplement_flags=result.supplement_flags,
        feeding_schedule=[FeedingScheduleItem(**s) for s in result.feeding_schedule],
        notes=result.notes,
        engine_version=result.engine_version,
        ai_insights=None,
        ai_provider_used=None,
        created_at=now,
        updated_at=now,
    )


@router.get("/{plan_id}", response_model=DietPlanPublic)
async def get_diet_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> DietPlanPublic:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diet plans are not persisted in anonymous mode.",
        )

    from app.services.diet_service import diet_service

    plan = await diet_service.get_by_id(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diet plan not found")
    return DietPlanPublic.model_validate(plan)


@router.get("", response_model=PaginatedResponse)
async def list_diet_plans(
    pet_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
) -> PaginatedResponse:
    if current_user:
        from app.services.diet_service import diet_service

        if pet_id:
            plans, total = await diet_service.list_by_pet(db, pet_id, current_user.id, page, page_size)
        else:
            plans, total = await diet_service.list_by_user(db, current_user.id, page, page_size)

        pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedResponse(
            items=[DietPlanPublic.model_validate(p) for p in plans],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, pages=0)
