from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.user import User


class PetWeightLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pet_weight_logs"
    __table_args__ = (
        Index("ix_pet_weight_logs_pet_id_measured_on", "pet_id", "measured_on"),
        Index("ix_pet_weight_logs_user_id_measured_on", "user_id", "measured_on"),
    )

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measured_on: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped[Pet] = relationship("Pet", back_populates="weight_logs")
    user: Mapped[User] = relationship("User", back_populates="weight_logs")
