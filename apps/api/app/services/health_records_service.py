from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pet import Pet
from app.models.pet_expense import PetExpense
from app.models.pet_health_record import PetHealthRecord
from app.models.pet_medication_schedule import PetMedicationSchedule
from app.models.pet_vaccination import PetVaccination
from app.schemas.health_records import (
    ExpenseCreate,
    ExpenseUpdate,
    HealthRecordCreate,
    HealthRecordUpdate,
    MedicationCreate,
    MedicationUpdate,
)

logger = logging.getLogger(__name__)


class HealthRecordsService:
    @staticmethod
    def _due_status(due_on: date, today: date | None = None) -> str:
        today = today or date.today()
        return "overdue" if due_on < today else "due_soon"

    async def pet_belongs_to_user(self, db: AsyncSession, pet_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(Pet.id).where(Pet.id == pet_id, Pet.user_id == user_id, Pet.deleted_at.is_(None))
        )
        return result.scalar_one_or_none() is not None

    async def create_health_record(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        data: HealthRecordCreate,
    ) -> PetHealthRecord:
        record = PetHealthRecord(
            user_id=user_id,
            pet_id=pet_id,
            record_type=data.record_type,
            title=data.title,
            details=data.details,
            recorded_on=data.recorded_on,
            veterinarian=data.veterinarian,
            clinic_name=data.clinic_name,
            next_visit_on=data.next_visit_on,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("Created health record id=%s pet_id=%s user_id=%s", record.id, pet_id, user_id)
        return record

    async def list_health_records(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PetHealthRecord], int]:
        base = select(PetHealthRecord).where(
            PetHealthRecord.user_id == user_id,
            PetHealthRecord.pet_id == pet_id,
        )
        total = (
            await db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = await db.execute(
            base.order_by(PetHealthRecord.recorded_on.desc(), PetHealthRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return rows.scalars().all(), total

    async def get_health_record_by_id(
        self, db: AsyncSession, user_id: uuid.UUID, record_id: uuid.UUID
    ) -> PetHealthRecord | None:
        result = await db.execute(
            select(PetHealthRecord).where(
                PetHealthRecord.id == record_id,
                PetHealthRecord.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_health_record(
        self,
        db: AsyncSession,
        record: PetHealthRecord,
        data: HealthRecordUpdate,
    ) -> PetHealthRecord:
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(record, key, value)
        await db.commit()
        await db.refresh(record)
        logger.info("Updated health record id=%s", record.id)
        return record

    async def delete_health_record(self, db: AsyncSession, record: PetHealthRecord) -> None:
        await db.delete(record)
        await db.commit()
        logger.info("Deleted health record id=%s", record.id)

    async def create_medication(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        data: MedicationCreate,
    ) -> PetMedicationSchedule:
        medication = PetMedicationSchedule(
            user_id=user_id,
            pet_id=pet_id,
            medication_name=data.medication_name,
            dosage=data.dosage,
            frequency=data.frequency,
            starts_on=data.starts_on,
            ends_on=data.ends_on,
            next_due_on=data.next_due_on,
            reminder_days_before=data.reminder_days_before,
            is_active=data.is_active,
            notes=data.notes,
        )
        db.add(medication)
        await db.commit()
        await db.refresh(medication)
        logger.info("Created medication schedule id=%s pet_id=%s user_id=%s", medication.id, pet_id, user_id)
        return medication

    async def list_medications(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PetMedicationSchedule], int]:
        base = select(PetMedicationSchedule).where(
            PetMedicationSchedule.user_id == user_id,
            PetMedicationSchedule.pet_id == pet_id,
        )
        total = (
            await db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = await db.execute(
            base.order_by(
                PetMedicationSchedule.is_active.desc(),
                PetMedicationSchedule.next_due_on.asc(),
                PetMedicationSchedule.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return rows.scalars().all(), total

    async def get_medication_by_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        medication_id: uuid.UUID,
    ) -> PetMedicationSchedule | None:
        result = await db.execute(
            select(PetMedicationSchedule).where(
                PetMedicationSchedule.id == medication_id,
                PetMedicationSchedule.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_medication(
        self,
        db: AsyncSession,
        medication: PetMedicationSchedule,
        data: MedicationUpdate,
    ) -> PetMedicationSchedule:
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(medication, key, value)
        await db.commit()
        await db.refresh(medication)
        logger.info("Updated medication schedule id=%s", medication.id)
        return medication

    async def delete_medication(self, db: AsyncSession, medication: PetMedicationSchedule) -> None:
        await db.delete(medication)
        await db.commit()
        logger.info("Deleted medication schedule id=%s", medication.id)

    async def create_expense(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        data: ExpenseCreate,
    ) -> PetExpense:
        expense = PetExpense(
            user_id=user_id,
            pet_id=pet_id,
            category=data.category,
            amount=data.amount,
            expense_on=data.expense_on,
            description=data.description,
            vendor=data.vendor,
            notes=data.notes,
        )
        db.add(expense)
        await db.commit()
        await db.refresh(expense)
        logger.info("Created expense id=%s pet_id=%s user_id=%s", expense.id, pet_id, user_id)
        return expense

    async def list_expenses(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PetExpense], int]:
        base = select(PetExpense).where(
            PetExpense.user_id == user_id,
            PetExpense.pet_id == pet_id,
        )
        total = (
            await db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = await db.execute(
            base.order_by(PetExpense.expense_on.desc(), PetExpense.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return rows.scalars().all(), total

    async def get_expense_by_id(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        expense_id: uuid.UUID,
    ) -> PetExpense | None:
        result = await db.execute(
            select(PetExpense).where(PetExpense.id == expense_id, PetExpense.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_expense(
        self,
        db: AsyncSession,
        expense: PetExpense,
        data: ExpenseUpdate,
    ) -> PetExpense:
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(expense, key, value)
        await db.commit()
        await db.refresh(expense)
        logger.info("Updated expense id=%s", expense.id)
        return expense

    async def delete_expense(self, db: AsyncSession, expense: PetExpense) -> None:
        await db.delete(expense)
        await db.commit()
        logger.info("Deleted expense id=%s", expense.id)

    async def get_reminders(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        window_days: int = 30,
        limit: int = 40,
    ) -> list[dict]:
        today = date.today()
        window_end = today + timedelta(days=window_days)

        pets_rows = (
            await db.execute(
                select(Pet.id, Pet.name).where(Pet.user_id == user_id, Pet.deleted_at.is_(None))
            )
        ).all()
        pet_name_map = {row.id: row.name for row in pets_rows}
        pet_ids = list(pet_name_map)
        if not pet_ids:
            return []

        reminders: list[dict] = []

        medication_rows = (
            await db.execute(
                select(PetMedicationSchedule)
                .where(
                    PetMedicationSchedule.user_id == user_id,
                    PetMedicationSchedule.is_active.is_(True),
                    PetMedicationSchedule.next_due_on.is_not(None),
                    PetMedicationSchedule.next_due_on <= window_end,
                    PetMedicationSchedule.pet_id.in_(pet_ids),
                )
                .order_by(PetMedicationSchedule.next_due_on.asc())
                .limit(limit)
            )
        ).scalars().all()
        for item in medication_rows:
            if item.next_due_on is None:
                continue
            reminders.append(
                {
                    "item_id": item.id,
                    "pet_id": item.pet_id,
                    "pet_name": pet_name_map.get(item.pet_id, "Unknown"),
                    "reminder_type": "medication",
                    "title": f"{item.medication_name} ({item.dosage})",
                    "due_on": item.next_due_on,
                    "days_until_due": (item.next_due_on - today).days,
                    "status": self._due_status(item.next_due_on, today),
                }
            )

        visit_rows = (
            await db.execute(
                select(PetHealthRecord)
                .where(
                    PetHealthRecord.user_id == user_id,
                    PetHealthRecord.next_visit_on.is_not(None),
                    PetHealthRecord.next_visit_on <= window_end,
                    PetHealthRecord.pet_id.in_(pet_ids),
                )
                .order_by(PetHealthRecord.next_visit_on.asc())
                .limit(limit)
            )
        ).scalars().all()
        for item in visit_rows:
            if item.next_visit_on is None:
                continue
            reminders.append(
                {
                    "item_id": item.id,
                    "pet_id": item.pet_id,
                    "pet_name": pet_name_map.get(item.pet_id, "Unknown"),
                    "reminder_type": "vet_visit",
                    "title": item.title,
                    "due_on": item.next_visit_on,
                    "days_until_due": (item.next_visit_on - today).days,
                    "status": self._due_status(item.next_visit_on, today),
                }
            )

        vaccination_rows = (
            await db.execute(
                select(PetVaccination)
                .where(
                    PetVaccination.user_id == user_id,
                    PetVaccination.is_completed.is_(False),
                    PetVaccination.due_on <= window_end,
                    PetVaccination.pet_id.in_(pet_ids),
                )
                .order_by(PetVaccination.due_on.asc())
                .limit(limit)
            )
        ).scalars().all()
        for item in vaccination_rows:
            reminders.append(
                {
                    "item_id": item.id,
                    "pet_id": item.pet_id,
                    "pet_name": pet_name_map.get(item.pet_id, "Unknown"),
                    "reminder_type": "vaccination",
                    "title": item.vaccine_name,
                    "due_on": item.due_on,
                    "days_until_due": (item.due_on - today).days,
                    "status": self._due_status(item.due_on, today),
                }
            )

        reminders.sort(key=lambda item: (item["due_on"], item["reminder_type"]))
        return reminders[:limit]

    async def get_summary(self, db: AsyncSession, user_id: uuid.UUID) -> dict:
        today = date.today()
        window_7d = today + timedelta(days=7)
        window_30d = today + timedelta(days=30)
        month_start = today.replace(day=1)

        total_records = (
            await db.execute(
                select(func.count())
                .select_from(PetHealthRecord)
                .where(PetHealthRecord.user_id == user_id)
            )
        ).scalar_one()

        active_medications = (
            await db.execute(
                select(func.count())
                .select_from(PetMedicationSchedule)
                .where(
                    PetMedicationSchedule.user_id == user_id,
                    PetMedicationSchedule.is_active.is_(True),
                    or_(
                        PetMedicationSchedule.ends_on.is_(None),
                        PetMedicationSchedule.ends_on >= today,
                    ),
                )
            )
        ).scalar_one()

        due_medications_7d = (
            await db.execute(
                select(func.count())
                .select_from(PetMedicationSchedule)
                .where(
                    PetMedicationSchedule.user_id == user_id,
                    PetMedicationSchedule.is_active.is_(True),
                    PetMedicationSchedule.next_due_on.is_not(None),
                    PetMedicationSchedule.next_due_on >= today,
                    PetMedicationSchedule.next_due_on <= window_7d,
                )
            )
        ).scalar_one()

        upcoming_visits_30d = (
            await db.execute(
                select(func.count())
                .select_from(PetHealthRecord)
                .where(
                    PetHealthRecord.user_id == user_id,
                    PetHealthRecord.next_visit_on.is_not(None),
                    PetHealthRecord.next_visit_on >= today,
                    PetHealthRecord.next_visit_on <= window_30d,
                )
            )
        ).scalar_one()

        monthly_expense_total_raw = (
            await db.execute(
                select(func.coalesce(func.sum(PetExpense.amount), 0))
                .where(
                    PetExpense.user_id == user_id,
                    PetExpense.expense_on >= month_start,
                )
            )
        ).scalar_one()
        monthly_expense_total = Decimal(str(monthly_expense_total_raw))

        expense_rows = (
            await db.execute(
                select(PetExpense.category, func.coalesce(func.sum(PetExpense.amount), 0).label("total"))
                .where(
                    PetExpense.user_id == user_id,
                    PetExpense.expense_on >= month_start,
                )
                .group_by(PetExpense.category)
                .order_by(PetExpense.category.asc())
            )
        ).all()
        expense_by_category = [
            {"category": row.category, "total_amount": Decimal(str(row.total))}
            for row in expense_rows
        ]

        reminders = await self.get_reminders(db, user_id, window_days=30, limit=40)

        return {
            "total_records": total_records,
            "active_medications": active_medications,
            "due_medications_7d": due_medications_7d,
            "upcoming_visits_30d": upcoming_visits_30d,
            "monthly_expense_total": monthly_expense_total,
            "expense_by_category": expense_by_category,
            "reminders": reminders,
        }


health_records_service = HealthRecordsService()
