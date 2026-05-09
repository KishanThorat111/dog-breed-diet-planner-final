from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.pet import Pet
    from app.models.upload import Upload
    from app.models.user import User


class AIPrediction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_predictions"
    __table_args__ = (
        # Time-based queries (history, recent activity)
        Index("ix_ai_predictions_created_at", "created_at"),
        # User's prediction history ordered by time
        Index("ix_ai_predictions_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="SET NULL"),
        nullable=True,
    )
    top_breed: Mapped[str] = mapped_column(String(100), nullable=False)
    top_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    all_predictions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )  # [{breed, confidence}]
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    inference_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", lazy="select")
    pet: Mapped[Pet | None] = relationship("Pet", back_populates="predictions")
    upload: Mapped[Upload] = relationship("Upload", lazy="select")
