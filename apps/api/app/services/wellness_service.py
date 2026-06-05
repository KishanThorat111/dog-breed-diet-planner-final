from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import Pet
from app.models.pet_vaccination import PetVaccination
from app.models.pet_weight_log import PetWeightLog
from app.schemas.wellness import VaccinationCreate, VaccinationUpdate, WeightLogCreate

logger = logging.getLogger(__name__)


class WellnessService:
    @staticmethod
    def vaccination_status(vaccination: PetVaccination, today: date | None = None) -> str:
        today = today or date.today()
        if vaccination.is_completed:
            return "completed"
        if vaccination.due_on < today:
            return "overdue"
        if vaccination.due_on <= today + timedelta(days=30):
            return "due_soon"
        return "scheduled"

    async def pet_belongs_to_user(self, db: AsyncSession, pet_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(Pet.id).where(Pet.id == pet_id, Pet.user_id == user_id, Pet.deleted_at.is_(None))
        )
        return result.scalar_one_or_none() is not None

    async def create_weight_log(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        data: WeightLogCreate,
    ) -> PetWeightLog:
        entry = PetWeightLog(
            user_id=user_id,
            pet_id=pet_id,
            measured_on=data.measured_on,
            weight_kg=data.weight_kg,
            notes=data.notes,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        logger.info("Created weight log id=%s pet_id=%s user_id=%s", entry.id, pet_id, user_id)
        return entry

    async def list_weight_logs(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PetWeightLog], int]:
        base = select(PetWeightLog).where(
            PetWeightLog.user_id == user_id,
            PetWeightLog.pet_id == pet_id,
        )
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        result = await db.execute(
            base.order_by(PetWeightLog.measured_on.desc(), PetWeightLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total

    async def get_weight_log_by_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        log_id: uuid.UUID,
    ) -> PetWeightLog | None:
        result = await db.execute(
            select(PetWeightLog).where(PetWeightLog.id == log_id, PetWeightLog.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete_weight_log(self, db: AsyncSession, log: PetWeightLog) -> None:
        await db.delete(log)
        await db.commit()
        logger.info("Deleted weight log id=%s", log.id)

    async def create_vaccination(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        data: VaccinationCreate,
    ) -> PetVaccination:
        vaccination = PetVaccination(
            user_id=user_id,
            pet_id=pet_id,
            vaccine_name=data.vaccine_name,
            due_on=data.due_on,
            administered_on=data.administered_on,
            is_completed=data.is_completed,
            reminder_days_before=data.reminder_days_before,
            notes=data.notes,
        )
        db.add(vaccination)
        await db.commit()
        await db.refresh(vaccination)
        logger.info("Created vaccination id=%s pet_id=%s user_id=%s", vaccination.id, pet_id, user_id)
        return vaccination

    async def list_vaccinations(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PetVaccination], int]:
        base = select(PetVaccination).where(
            PetVaccination.user_id == user_id,
            PetVaccination.pet_id == pet_id,
        )
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        result = await db.execute(
            base.order_by(PetVaccination.due_on.asc(), PetVaccination.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total

    async def get_vaccination_by_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        vaccination_id: uuid.UUID,
    ) -> PetVaccination | None:
        result = await db.execute(
            select(PetVaccination).where(
                PetVaccination.id == vaccination_id,
                PetVaccination.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_vaccination(
        self,
        db: AsyncSession,
        vaccination: PetVaccination,
        data: VaccinationUpdate,
    ) -> PetVaccination:
        update_data = data.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(vaccination, key, value)
        await db.commit()
        await db.refresh(vaccination)
        logger.info("Updated vaccination id=%s", vaccination.id)
        return vaccination

    async def delete_vaccination(self, db: AsyncSession, vaccination: PetVaccination) -> None:
        await db.delete(vaccination)
        await db.commit()
        logger.info("Deleted vaccination id=%s", vaccination.id)

    async def get_summary(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        today = date.today()
        window_end = today + timedelta(days=30)

        pets_result = await db.execute(
            select(Pet.id, Pet.name)
            .where(Pet.user_id == user_id, Pet.deleted_at.is_(None))
            .order_by(Pet.name.asc())
        )
        pet_rows = pets_result.all()
        pet_ids = [row.id for row in pet_rows]

        if not pet_ids:
            return {
                "total_pets": 0,
                "pets_with_weight_logs": 0,
                "upcoming_vaccinations": 0,
                "overdue_vaccinations": 0,
                "pet_trends": [],
                "reminders": [],
            }

        weight_result = await db.execute(
            select(
                PetWeightLog.pet_id,
                PetWeightLog.weight_kg,
                PetWeightLog.measured_on,
            )
            .where(PetWeightLog.user_id == user_id, PetWeightLog.pet_id.in_(pet_ids))
            .order_by(PetWeightLog.pet_id.asc(), PetWeightLog.measured_on.desc(), PetWeightLog.created_at.desc())
        )

        top_two_by_pet: dict[uuid.UUID, list[tuple[Decimal, date]]] = {}
        for row in weight_result.all():
            bucket = top_two_by_pet.setdefault(row.pet_id, [])
            if len(bucket) < 2:
                bucket.append((row.weight_kg, row.measured_on))

        pet_trends: list[dict] = []
        for row in pet_rows:
            values = top_two_by_pet.get(row.id, [])
            latest = values[0][0] if values else None
            previous = values[1][0] if len(values) > 1 else None
            delta = (latest - previous) if latest is not None and previous is not None else None

            if latest is None:
                trend = "no_data"
            elif previous is None:
                trend = "baseline"
            elif abs(delta) < Decimal("0.05"):
                trend = "stable"
            elif delta > 0:
                trend = "up"
            else:
                trend = "down"

            pet_trends.append(
                {
                    "pet_id": row.id,
                    "pet_name": row.name,
                    "latest_weight_kg": latest,
                    "previous_weight_kg": previous,
                    "delta_kg": delta,
                    "trend": trend,
                }
            )

        pets_with_weight_logs = sum(1 for p in pet_trends if p["latest_weight_kg"] is not None)

        overdue_result = await db.execute(
            select(func.count())
            .select_from(PetVaccination)
            .where(
                PetVaccination.user_id == user_id,
                PetVaccination.is_completed.is_(False),
                PetVaccination.due_on < today,
                PetVaccination.pet_id.in_(pet_ids),
            )
        )
        overdue = overdue_result.scalar_one()

        upcoming_result = await db.execute(
            select(func.count())
            .select_from(PetVaccination)
            .where(
                PetVaccination.user_id == user_id,
                PetVaccination.is_completed.is_(False),
                PetVaccination.due_on >= today,
                PetVaccination.due_on <= window_end,
                PetVaccination.pet_id.in_(pet_ids),
            )
        )
        upcoming = upcoming_result.scalar_one()

        reminder_result = await db.execute(
            select(PetVaccination, Pet.name)
            .join(Pet, Pet.id == PetVaccination.pet_id)
            .where(
                PetVaccination.user_id == user_id,
                PetVaccination.is_completed.is_(False),
                PetVaccination.due_on <= window_end,
                Pet.deleted_at.is_(None),
            )
            .order_by(PetVaccination.due_on.asc())
            .limit(25)
        )

        reminders: list[dict] = []
        for vaccination, pet_name in reminder_result.all():
            status = self.vaccination_status(vaccination, today)
            reminders.append(
                {
                    "vaccination_id": vaccination.id,
                    "pet_id": vaccination.pet_id,
                    "pet_name": pet_name,
                    "vaccine_name": vaccination.vaccine_name,
                    "due_on": vaccination.due_on,
                    "days_until_due": (vaccination.due_on - today).days,
                    "status": status,
                }
            )

        return {
            "total_pets": len(pet_ids),
            "pets_with_weight_logs": pets_with_weight_logs,
            "upcoming_vaccinations": upcoming,
            "overdue_vaccinations": overdue,
            "pet_trends": pet_trends,
            "reminders": reminders,
        }


wellness_service = WellnessService()
