from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.diet_plan import DietPlanGenerateRequest, DietPlanPublic, FoodRecommendation, FeedingScheduleItem
from app.services.diet_service import diet_service
from app.services.pet_service import pet_service

router = APIRouter()


@router.post("/generate", response_model=DietPlanPublic, status_code=status.HTTP_201_CREATED)
async def generate_diet_plan(
    request: DietPlanGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DietPlanPublic:
    """Generate a personalized diet plan for a pet using the NRC/AAFCO-based engine."""
    pet = await pet_service.get_by_id(db, request.pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    plan = await diet_service.generate_for_pet(db, current_user.id, request, pet)
    return _to_public(plan)


@router.get("/{plan_id}", response_model=DietPlanPublic)
async def get_diet_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DietPlanPublic:
    plan = await diet_service.get_by_id(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diet plan not found")
    return _to_public(plan)


@router.get("", response_model=PaginatedResponse)
async def list_diet_plans(
    pet_id: uuid.UUID | None = Query(None),  # optional — if absent, list all plans for user
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if pet_id is not None:
        # Validate pet belongs to user
        pet = await pet_service.get_by_id(db, pet_id, current_user.id)
        if not pet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
        plans, total = await diet_service.list_by_pet(db, pet_id, current_user.id, page, page_size)
    else:
        plans, total = await diet_service.list_by_user(db, current_user.id, page, page_size)

    return PaginatedResponse(
        items=[_to_public(p) for p in plans],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


def _to_public(plan) -> DietPlanPublic:  # type: ignore[no-untyped-def]
    return DietPlanPublic(
        id=plan.id,
        pet_id=plan.pet_id,
        user_id=plan.user_id,
        prediction_id=plan.prediction_id,
        breed=plan.breed,
        age_months=plan.age_months,
        weight_kg=plan.weight_kg,
        activity_level=plan.activity_level,
        daily_calories=plan.daily_calories,
        protein_g=plan.protein_g,
        fat_g=plan.fat_g,
        carbs_g=plan.carbs_g,
        meals_per_day=plan.meals_per_day,
        food_recommendations=[FoodRecommendation(**f) for f in plan.food_recommendations],
        foods_to_avoid=plan.foods_to_avoid,
        supplement_flags=plan.supplement_flags,
        feeding_schedule=[FeedingScheduleItem(**s) for s in plan.feeding_schedule],
        notes=plan.notes,
        engine_version=plan.engine_version,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )
