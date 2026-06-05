from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.schemas.common import APIBaseModel


class WeightLogCreate(APIBaseModel):
    measured_on: date
    weight_kg: Annotated[Decimal, Field(ge=Decimal("0.1"), le=Decimal("200"))]
    notes: str | None = None


class WeightLogPublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    measured_on: date
    weight_kg: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class VaccinationCreate(APIBaseModel):
    vaccine_name: Annotated[str, Field(min_length=2, max_length=120)]
    due_on: date
    administered_on: date | None = None
    is_completed: bool = False
    reminder_days_before: Annotated[int, Field(ge=0, le=60)] = 7
    notes: str | None = None


class VaccinationUpdate(APIBaseModel):
    vaccine_name: Annotated[str | None, Field(min_length=2, max_length=120)] = None
    due_on: date | None = None
    administered_on: date | None = None
    is_completed: bool | None = None
    reminder_days_before: Annotated[int | None, Field(ge=0, le=60)] = None
    notes: str | None = None


class VaccinationPublic(APIBaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    user_id: uuid.UUID
    vaccine_name: str
    due_on: date
    administered_on: date | None
    is_completed: bool
    reminder_days_before: int
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class WellnessPetTrend(APIBaseModel):
    pet_id: uuid.UUID
    pet_name: str
    latest_weight_kg: Decimal | None = None
    previous_weight_kg: Decimal | None = None
    delta_kg: Decimal | None = None
    trend: str


class WellnessReminder(APIBaseModel):
    vaccination_id: uuid.UUID
    pet_id: uuid.UUID
    pet_name: str
    vaccine_name: str
    due_on: date
    days_until_due: int
    status: str


class WellnessSummaryPublic(APIBaseModel):
    total_pets: int
    pets_with_weight_logs: int
    upcoming_vaccinations: int
    overdue_vaccinations: int
    pet_trends: list[WellnessPetTrend]
    reminders: list[WellnessReminder]
