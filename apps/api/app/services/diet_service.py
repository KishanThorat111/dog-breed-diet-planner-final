from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diet_plan import DietPlan
from app.models.pet import Pet
from app.schemas.diet_plan import DietPlanGenerateRequest
from app.services.diet_engine import diet_engine

logger = logging.getLogger(__name__)


class DietService:
    async def generate_for_pet(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        request: DietPlanGenerateRequest,
        pet: Pet,
    ) -> DietPlan:
        # Use request overrides or fall back to pet profile values
        breed = request.breed or pet.breed or "unknown"
        age_months = request.age_months if request.age_months is not None else (pet.age_months or 24)
        weight_kg = float(request.weight_kg or pet.weight_kg or 10)
        activity_level = request.activity_level or pet.activity_level or "moderate"

        # Run deterministic diet calculation (always succeeds, no external deps)
        result = diet_engine.generate(
            breed=breed,
            age_months=age_months,
            weight_kg=weight_kg,
            activity_level=activity_level,
            is_neutered=pet.is_neutered,
            sex=pet.sex or "male",
            allergies=list(pet.allergies),
            health_conditions=list(pet.health_conditions),
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
                health_conditions=list(pet.health_conditions),
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
