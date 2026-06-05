from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.user import User


class PetVaccination(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pet_vaccinations"
    __table_args__ = (
        Index("ix_pet_vaccinations_pet_id_due_on", "pet_id", "due_on"),
        Index("ix_pet_vaccinations_user_id_due_on", "user_id", "due_on"),
        Index("ix_pet_vaccinations_due_on_completed", "due_on", "is_completed"),
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
    vaccine_name: Mapped[str] = mapped_column(String(120), nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    administered_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped[Pet] = relationship("Pet", back_populates="vaccinations")
    user: Mapped[User] = relationship("User", back_populates="vaccinations")
