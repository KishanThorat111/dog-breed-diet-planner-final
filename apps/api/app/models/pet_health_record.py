from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.user import User


class PetHealthRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pet_health_records"
    __table_args__ = (
        Index("ix_pet_health_records_pet_id_recorded_on", "pet_id", "recorded_on"),
        Index("ix_pet_health_records_user_id_recorded_on", "user_id", "recorded_on"),
        Index("ix_pet_health_records_next_visit_on", "next_visit_on"),
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

    record_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    veterinarian: Mapped[str | None] = mapped_column(String(150), nullable=True)
    clinic_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    next_visit_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    pet: Mapped[Pet] = relationship("Pet", back_populates="health_records")
    user: Mapped[User] = relationship("User", back_populates="health_records")
