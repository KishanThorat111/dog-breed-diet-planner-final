from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.health_records import (
    ExpenseCreate,
    ExpensePublic,
    ExpenseUpdate,
    HealthRecordCreate,
    HealthRecordPublic,
    HealthRecordUpdate,
    HealthReminder,
    HealthSummaryPublic,
    MedicationCreate,
    MedicationPublic,
    MedicationUpdate,
)
from app.services.health_records_service import health_records_service

router = APIRouter()


@router.get("/summary", response_model=HealthSummaryPublic)
async def get_health_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthSummaryPublic:
    payload = await health_records_service.get_summary(db, current_user.id)
    return HealthSummaryPublic.model_validate(payload)


@router.get("/reminders", response_model=list[HealthReminder])
async def list_reminders(
    window_days: int = Query(30, ge=1, le=90),
    limit: int = Query(40, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HealthReminder]:
    items = await health_records_service.get_reminders(db, current_user.id, window_days=window_days, limit=limit)
    return [HealthReminder.model_validate(item) for item in items]


@router.get("/pets/{pet_id}/records", response_model=PaginatedResponse)
async def list_health_records(
    pet_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    items, total = await health_records_service.list_health_records(db, current_user.id, pet_id, page, page_size)
    return PaginatedResponse(
        items=[HealthRecordPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("/pets/{pet_id}/records", response_model=HealthRecordPublic, status_code=status.HTTP_201_CREATED)
async def create_health_record(
    pet_id: uuid.UUID,
    data: HealthRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthRecordPublic:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    record = await health_records_service.create_health_record(db, current_user.id, pet_id, data)
    return HealthRecordPublic.model_validate(record)


@router.patch("/records/{record_id}", response_model=HealthRecordPublic)
async def update_health_record(
    record_id: uuid.UUID,
    data: HealthRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthRecordPublic:
    record = await health_records_service.get_health_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found")
    updated = await health_records_service.update_health_record(db, record, data)
    return HealthRecordPublic.model_validate(updated)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = await health_records_service.get_health_record_by_id(db, current_user.id, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Health record not found")
    await health_records_service.delete_health_record(db, record)


@router.get("/pets/{pet_id}/medications", response_model=PaginatedResponse)
async def list_medications(
    pet_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    items, total = await health_records_service.list_medications(db, current_user.id, pet_id, page, page_size)
    return PaginatedResponse(
        items=[MedicationPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post(
    "/pets/{pet_id}/medications",
    response_model=MedicationPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_medication(
    pet_id: uuid.UUID,
    data: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicationPublic:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    item = await health_records_service.create_medication(db, current_user.id, pet_id, data)
    return MedicationPublic.model_validate(item)


@router.patch("/medications/{medication_id}", response_model=MedicationPublic)
async def update_medication(
    medication_id: uuid.UUID,
    data: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicationPublic:
    item = await health_records_service.get_medication_by_id(db, current_user.id, medication_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication schedule not found")
    updated = await health_records_service.update_medication(db, item, data)
    return MedicationPublic.model_validate(updated)


@router.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    item = await health_records_service.get_medication_by_id(db, current_user.id, medication_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication schedule not found")
    await health_records_service.delete_medication(db, item)


@router.get("/pets/{pet_id}/expenses", response_model=PaginatedResponse)
async def list_expenses(
    pet_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    items, total = await health_records_service.list_expenses(db, current_user.id, pet_id, page, page_size)
    return PaginatedResponse(
        items=[ExpensePublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("/pets/{pet_id}/expenses", response_model=ExpensePublic, status_code=status.HTTP_201_CREATED)
async def create_expense(
    pet_id: uuid.UUID,
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpensePublic:
    if not await health_records_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    item = await health_records_service.create_expense(db, current_user.id, pet_id, data)
    return ExpensePublic.model_validate(item)


@router.patch("/expenses/{expense_id}", response_model=ExpensePublic)
async def update_expense(
    expense_id: uuid.UUID,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpensePublic:
    item = await health_records_service.get_expense_by_id(db, current_user.id, expense_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    updated = await health_records_service.update_expense(db, item, data)
    return ExpensePublic.model_validate(updated)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    item = await health_records_service.get_expense_by_id(db, current_user.id, expense_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    await health_records_service.delete_expense(db, item)
