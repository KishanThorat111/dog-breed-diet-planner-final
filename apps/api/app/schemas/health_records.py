from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.common import APIBaseModel

HEALTH_RECORD_TYPES = {"diagnosis", "vet_note", "visit", "lab_result", "symptom", "other"}
EXPENSE_CATEGORIES = {"food", "medicine", "vaccine", "vet_visit", "accessory", "other"}


class HealthRecordCreate(APIBaseModel):
    record_type: str
    title: Annotated[str, Field(min_length=2, max_length=150)]
    details: Annotated[str, Field(min_length=2, max_length=4000)]
    recorded_on: date
    veterinarian: Annotated[str | None, Field(max_length=150)] = None
    clinic_name: Annotated[str | None, Field(max_length=150)] = None
    next_visit_on: date | None = None

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in HEALTH_RECORD_TYPES:
            raise ValueError(f"record_type must be one of: {sorted(HEALTH_RECORD_TYPES)}")
        return normalized


class HealthRecordUpdate(APIBaseModel):
    record_type: str | None = None
    title: Annotated[str | None, Field(min_length=2, max_length=150)] = None
    details: Annotated[str | None, Field(min_length=2, max_length=4000)] = None
    recorded_on: date | None = None
    veterinarian: Annotated[str | None, Field(max_length=150)] = None
    clinic_name: Annotated[str | None, Field(max_length=150)] = None
    next_visit_on: date | None = None

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in HEALTH_RECORD_TYPES:
            raise ValueError(f"record_type must be one of: {sorted(HEALTH_RECORD_TYPES)}")
        return normalized


class HealthRecordPublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    record_type: str
    title: str
    details: str
    recorded_on: date
    veterinarian: str | None
    clinic_name: str | None
    next_visit_on: date | None
    created_at: datetime
    updated_at: datetime


class MedicationCreate(APIBaseModel):
    medication_name: Annotated[str, Field(min_length=2, max_length=120)]
    dosage: Annotated[str, Field(min_length=1, max_length=80)]
    frequency: Annotated[str, Field(min_length=1, max_length=60)]
    starts_on: date
    ends_on: date | None = None
    next_due_on: date | None = None
    reminder_days_before: Annotated[int, Field(ge=0, le=30)] = 1
    is_active: bool = True
    notes: Annotated[str | None, Field(max_length=2000)] = None


class MedicationUpdate(APIBaseModel):
    medication_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    dosage: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    frequency: Annotated[str | None, Field(min_length=1, max_length=60)] = None
    starts_on: date | None = None
    ends_on: date | None = None
    next_due_on: date | None = None
    reminder_days_before: Annotated[int | None, Field(ge=0, le=30)] = None
    is_active: bool | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None


class MedicationPublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    medication_name: str
    dosage: str
    frequency: str
    starts_on: date
    ends_on: date | None
    next_due_on: date | None
    reminder_days_before: int
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ExpenseCreate(APIBaseModel):
    category: str
    amount: Annotated[Decimal, Field(gt=Decimal("0"), le=Decimal("1000000"))]
    expense_on: date
    description: Annotated[str, Field(min_length=2, max_length=255)]
    vendor: Annotated[str | None, Field(max_length=120)] = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of: {sorted(EXPENSE_CATEGORIES)}")
        return normalized


class ExpenseUpdate(APIBaseModel):
    category: str | None = None
    amount: Annotated[Decimal | None, Field(gt=Decimal("0"), le=Decimal("1000000"))] = None
    expense_on: date | None = None
    description: Annotated[str | None, Field(min_length=2, max_length=255)] = None
    vendor: Annotated[str | None, Field(max_length=120)] = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of: {sorted(EXPENSE_CATEGORIES)}")
        return normalized


class ExpensePublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    category: str
    amount: Decimal
    expense_on: date
    description: str
    vendor: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ExpenseCategorySummary(APIBaseModel):
    category: str
    total_amount: Decimal


class HealthReminder(APIBaseModel):
    item_id: uuid.UUID
    pet_id: uuid.UUID
    pet_name: str
    reminder_type: str
    title: str
    due_on: date
    days_until_due: int
    status: str


class HealthSummaryPublic(APIBaseModel):
    total_records: int
    active_medications: int
    due_medications_7d: int
    upcoming_visits_30d: int
    monthly_expense_total: Decimal
    expense_by_category: list[ExpenseCategorySummary]
    reminders: list[HealthReminder]
