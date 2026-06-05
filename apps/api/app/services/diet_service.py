from __future__ import annotations

import logging
import math
import re
import uuid
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_plan import DietPlan
from app.models.pet import Pet
from app.schemas.diet_plan import DietPlanGenerateRequest
from app.services.diet_engine import diet_engine

logger = logging.getLogger(__name__)

_ALLOWED_ACTIVITY_LEVELS = {"sedentary", "light", "moderate", "active", "very_active"}

_DIET_PLAN_JSON_COLUMNS = (
    "food_recommendations",
    "foods_to_avoid",
    "supplement_flags",
    "feeding_schedule",
)


def _normalize_breed(value: object | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "mixed_breed"
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "mixed_breed"


def _normalize_age_months(value: object | None) -> int:
    try:
        age = int(value)  # type: ignore[arg-type]
    except Exception:
        return 24
    return max(0, min(age, 360))


def _normalize_weight_kg(value: object | None) -> float:
    try:
        weight = float(value)  # type: ignore[arg-type]
    except Exception:
        return 10.0
    if not math.isfinite(weight) or weight <= 0:
        return 10.0
    return max(0.1, min(weight, 200.0))


def _normalize_activity(value: object | None) -> str:
    activity = str(value or "").strip().lower()
    return activity if activity in _ALLOWED_ACTIVITY_LEVELS else "moderate"


def _normalize_text_list(value: object | None) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    else:
        return []

    normalized: list[str] = []
    for item in items:
        text = str(item).strip().lower()
        if text and text not in {"none", "null"}:
            normalized.append(text)
    return normalized


def _is_missing_diet_plan_column_error(exc: Exception) -> bool:
    text_value = str(exc).lower()
    if "diet_plans" not in text_value:
        return False
    if "does not exist" not in text_value and "no such column" not in text_value:
        return False
    return any(column in text_value for column in _DIET_PLAN_JSON_COLUMNS)


async def _ensure_diet_plan_columns(db: AsyncSession) -> None:
    """Add missing diet_plans JSON columns on legacy databases and backfill defaults."""
    await db.execute(
        text("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS food_recommendations JSONB")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS foods_to_avoid JSONB")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS supplement_flags JSONB")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ADD COLUMN IF NOT EXISTS feeding_schedule JSONB")
    )

    # Backfill from historical column where available, then enforce non-null defaults.
    has_recommendations = (
        await db.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'diet_plans' AND column_name = 'recommendations'
                LIMIT 1
                """
            )
        )
    ).scalar_one_or_none() is not None

    if has_recommendations:
        await db.execute(
            text(
                """
                UPDATE diet_plans
                SET food_recommendations = COALESCE(food_recommendations, recommendations, '[]'::jsonb),
                    foods_to_avoid = COALESCE(foods_to_avoid, '[]'::jsonb),
                    supplement_flags = COALESCE(supplement_flags, '[]'::jsonb),
                    feeding_schedule = COALESCE(feeding_schedule, '[]'::jsonb)
                """
            )
        )
    else:
        await db.execute(
            text(
                """
                UPDATE diet_plans
                SET food_recommendations = COALESCE(food_recommendations, '[]'::jsonb),
                    foods_to_avoid = COALESCE(foods_to_avoid, '[]'::jsonb),
                    supplement_flags = COALESCE(supplement_flags, '[]'::jsonb),
                    feeding_schedule = COALESCE(feeding_schedule, '[]'::jsonb)
                """
            )
        )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN food_recommendations SET DEFAULT '[]'::jsonb")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN foods_to_avoid SET DEFAULT '[]'::jsonb")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN supplement_flags SET DEFAULT '[]'::jsonb")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN feeding_schedule SET DEFAULT '[]'::jsonb")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN food_recommendations SET NOT NULL")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN foods_to_avoid SET NOT NULL")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN supplement_flags SET NOT NULL")
    )
    await db.execute(
        text("ALTER TABLE diet_plans ALTER COLUMN feeding_schedule SET NOT NULL")
    )
    await db.commit()


class DietService:
    async def generate_for_pet(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        request: DietPlanGenerateRequest,
        pet: Pet,
    ) -> DietPlan:
        # Use request overrides or fall back to pet profile values
        breed = _normalize_breed(request.breed or pet.breed)
        age_months = _normalize_age_months(request.age_months if request.age_months is not None else pet.age_months)
        weight_kg = _normalize_weight_kg(request.weight_kg if request.weight_kg is not None else pet.weight_kg)
        activity_level = _normalize_activity(request.activity_level or pet.activity_level)
        allergies = _normalize_text_list(pet.allergies)
        health_conditions = _normalize_text_list(pet.health_conditions)

        # Run deterministic diet calculation (always succeeds, no external deps)
        try:
            result = diet_engine.generate(
                breed=breed,
                age_months=age_months,
                weight_kg=weight_kg,
                activity_level=activity_level,
                is_neutered=pet.is_neutered,
                sex=pet.sex or "male",
                allergies=allergies,
                health_conditions=health_conditions,
            )
        except Exception as exc:
            logger.exception(
                "Diet engine failed for pet_id=%s user_id=%s. Falling back to safe defaults. err=%s",
                pet.id,
                user_id,
                exc,
            )
            result = diet_engine.generate(
                breed="mixed_breed",
                age_months=24,
                weight_kg=10.0,
                activity_level="moderate",
                is_neutered=True,
                sex="male",
                allergies=[],
                health_conditions=[],
            )

        # Optional AI enrichment — non-blocking, never raises
        ai_insights = None
        ai_provider_used = None
        try:
            from app.services.ai_service import enrich_diet_plan
            ai_insights = await enrich_diet_plan(
                breed=breed,
                age_months=age_months,
                weight_kg=weight_kg,
                activity_level=activity_level,
                is_neutered=pet.is_neutered,
                sex=pet.sex or "male",
                daily_calories=result.daily_calories,
                protein_g=float(result.protein_g),
                fat_g=float(result.fat_g),
                supplement_flags=result.supplement_flags,
                foods_to_avoid=result.foods_to_avoid,
                health_conditions=health_conditions,
                user_id=user_id,
                reference_type="prediction",
                reference_id=request.prediction_id,
            )
            if ai_insights:
                ai_provider_used = ai_insights.pop("_provider", None)
                ai_insights.pop("_model", None)  # strip internal attribution fields
        except Exception as exc:
            # AI enrichment is non-critical — log and continue
            logger.warning("AI enrichment error (non-fatal): %s", exc)

        # Persist plan
        plan = DietPlan(
            pet_id=pet.id,
            user_id=user_id,
            prediction_id=request.prediction_id,
            breed=result.breed,
            age_months=result.age_months,
            weight_kg=Decimal(str(result.weight_kg)),
            activity_level=result.activity_level,
            daily_calories=result.daily_calories,
            protein_g=Decimal(str(result.protein_g)),
            fat_g=Decimal(str(result.fat_g)),
            carbs_g=Decimal(str(result.carbs_g)),
            meals_per_day=result.meals_per_day,
            food_recommendations=result.food_recommendations,
            foods_to_avoid=result.foods_to_avoid,
            supplement_flags=result.supplement_flags,
            feeding_schedule=result.feeding_schedule,
            notes=result.notes,
            engine_version=result.engine_version,
            ai_insights=ai_insights,
            ai_provider_used=ai_provider_used,
        )
        db.add(plan)
        try:
            await db.commit()
        except ProgrammingError as exc:
            await db.rollback()
            if not _is_missing_diet_plan_column_error(exc):
                raise

            logger.warning(
                "Detected legacy diet_plans schema during save; applying compatibility columns and retrying. err=%s",
                exc,
            )
            await _ensure_diet_plan_columns(db)
            db.add(plan)
            await db.commit()
        await db.refresh(plan)
        logger.info(
            "Generated diet plan id=%s for pet_id=%s ai_enriched=%s",
            plan.id, pet.id, ai_insights is not None,
        )
        return plan


    async def get_by_id(
        self, db: AsyncSession, plan_id: uuid.UUID, user_id: uuid.UUID
    ) -> DietPlan | None:
        result = await db.execute(
            select(DietPlan).where(
                DietPlan.id == plan_id, DietPlan.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_pet(
        self, db: AsyncSession, pet_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, page_size: int = 10
    ) -> tuple[list[DietPlan], int]:
        from sqlalchemy import func
        base = select(DietPlan).where(
            DietPlan.pet_id == pet_id, DietPlan.user_id == user_id
        )
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await db.execute(
            base.order_by(DietPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total  # type: ignore[return-value]

    async def list_by_user(
        self, db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 10
    ) -> tuple[list[DietPlan], int]:
        """List all diet plans for a user regardless of pet."""
        from sqlalchemy import func
        base = select(DietPlan).where(DietPlan.user_id == user_id)
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await db.execute(
            base.order_by(DietPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total  # type: ignore[return-value]


diet_service = DietService()
