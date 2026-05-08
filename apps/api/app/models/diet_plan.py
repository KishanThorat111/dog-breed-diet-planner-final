from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.prediction import AIPrediction
    from app.models.user import User


class DietPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "diet_plans"
    __table_args__ = (
        # Pet's diet plan list is a frequent access pattern
        Index("ix_diet_plans_pet_id_created_at", "pet_id", "created_at"),
        # User's all-plans listing
        Index("ix_diet_plans_user_id_created_at", "user_id", "created_at"),
    )

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_predictions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Input parameters used to generate this plan
    breed: Mapped[str] = mapped_column(String(100), nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    activity_level: Mapped[str] = mapped_column(String(20), nullable=False)

    # Calculated nutritional targets
    daily_calories: Mapped[int] = mapped_column(Integer, nullable=False)  # kcal/day
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)

    # Recommendations
    food_recommendations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    foods_to_avoid: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    supplement_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    feeding_schedule: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # AI-generated enrichment (optional — null if AI not configured or disabled)
    ai_insights: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Which provider generated the insights (e.g. 'gemini', 'openai') — never stores the key
    ai_provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    pet: Mapped[Pet] = relationship("Pet", back_populates="diet_plans")
    user: Mapped[User] = relationship("User", lazy="select")
    prediction: Mapped[AIPrediction | None] = relationship("AIPrediction", lazy="select")
