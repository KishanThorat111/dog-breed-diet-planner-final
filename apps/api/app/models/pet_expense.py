from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.user import User


class PetExpense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pet_expenses"
    __table_args__ = (
        Index("ix_pet_expenses_pet_id_expense_on", "pet_id", "expense_on"),
        Index("ix_pet_expenses_user_id_expense_on", "user_id", "expense_on"),
        Index("ix_pet_expenses_user_id_category", "user_id", "category"),
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

    category: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    expense_on: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped[Pet] = relationship("Pet", back_populates="expenses")
    user: Mapped[User] = relationship("User", back_populates="expenses")
