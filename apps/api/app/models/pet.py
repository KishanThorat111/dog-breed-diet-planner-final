from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.diet_plan import DietPlan
    from app.models.prediction import AIPrediction
    from app.models.user import User


class Pet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pets"
    __table_args__ = (
        # Soft-delete filter is on every query — must be indexed
        Index("ix_pets_deleted_at", "deleted_at"),
        # List pets by user is the most common access pattern
        Index("ix_pets_user_id_deleted_at", "user_id", "deleted_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # sex: "male" | "female" — neutering is captured separately in is_neutered
    # Frontend sends "male_neutered"/"female_spayed"; the router/schema splits these.
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_neutered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # life_stage: "puppy" | "adult" | "senior"
    life_stage: Mapped[str] = mapped_column(String(20), default="adult", nullable=False)

    activity_level: Mapped[str] = mapped_column(
        String(20), default="moderate", nullable=False
    )  # sedentary | light | moderate | active | very_active
    allergies: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    health_conditions: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="pets")
    predictions: Mapped[list[AIPrediction]] = relationship(
        "AIPrediction", back_populates="pet", lazy="select"
    )
    diet_plans: Mapped[list[DietPlan]] = relationship(
        "DietPlan", back_populates="pet", lazy="select"
    )
