from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import Pet
from app.schemas.pet import PetCreate, PetUpdate

logger = logging.getLogger(__name__)


class PetService:
    async def create(self, db: AsyncSession, user_id: uuid.UUID, data: PetCreate) -> Pet:
        pet = Pet(user_id=user_id, **data.model_dump())
        db.add(pet)
        await db.commit()
        await db.refresh(pet)
        logger.info("Created pet id=%s for user_id=%s", pet.id, user_id)
        return pet

    async def get_by_id(
        self, db: AsyncSession, pet_id: uuid.UUID, user_id: uuid.UUID
    ) -> Pet | None:
        result = await db.execute(
            select(Pet).where(
                Pet.id == pet_id,
                Pet.user_id == user_id,
                Pet.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_admin(self, db: AsyncSession, pet_id: uuid.UUID) -> Pet | None:
        result = await db.execute(
            select(Pet).where(Pet.id == pet_id, Pet.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Pet], int]:
        base = select(Pet).where(Pet.user_id == user_id, Pet.deleted_at.is_(None))

        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        result = await db.execute(
            base.order_by(Pet.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all(), total  # type: ignore[return-value]

    async def update(
        self, db: AsyncSession, pet: Pet, data: PetUpdate
    ) -> Pet:
        update_data = data.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(pet, key, value)
        await db.commit()
        await db.refresh(pet)
        return pet

    async def soft_delete(self, db: AsyncSession, pet: Pet) -> None:
        pet.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Soft-deleted pet id=%s", pet.id)


pet_service = PetService()
