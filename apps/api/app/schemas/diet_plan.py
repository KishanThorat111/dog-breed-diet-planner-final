from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.schemas.common import APIBaseModel


class FoodRecommendation(APIBaseModel):
    name: str
    amount_g: float
    notes: str | None = None
    category: str  # protein | carb | vegetable | supplement


class FeedingScheduleItem(APIBaseModel):
    meal_name: str  # Breakfast | Lunch | Dinner
    time_suggestion: str  # e.g. "7:00 AM"
    amount_g: float
    amount_kcal: int


class DietPlanGenerateRequest(APIBaseModel):
    pet_id: uuid.UUID
    prediction_id: uuid.UUID | None = None
    # If breed/age/weight not provided, they'll be read from the pet profile
    breed: str | None = None
    age_months: Annotated[int | None, Field(ge=0, le=360)] = None
    weight_kg: Annotated[Decimal | None, Field(ge=Decimal("0.1"), le=Decimal("200"))] = None
    activity_level: str | None = None


class DietPlanPublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    prediction_id: uuid.UUID | None
    breed: str
    age_months: int
    weight_kg: Decimal
    activity_level: str
    daily_calories: int
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    meals_per_day: int
    food_recommendations: list[FoodRecommendation]
    foods_to_avoid: list[str]
    supplement_flags: list[str]
    feeding_schedule: list[FeedingScheduleItem]
    notes: str | None
    engine_version: str
    # AI-generated insights (null when AI is disabled or unconfigured)
    ai_insights: dict | None = None
    ai_provider_used: str | None = None
    created_at: datetime
    updated_at: datetime
