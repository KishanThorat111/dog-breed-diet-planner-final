from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.wellness import (
    VaccinationCreate,
    VaccinationPublic,
    VaccinationUpdate,
    WeightLogCreate,
    WeightLogPublic,
    WellnessSummaryPublic,
)
from app.services.wellness_service import wellness_service

router = APIRouter()


def _to_vaccination_public(vaccination) -> VaccinationPublic:
    return VaccinationPublic(
        id=vaccination.id,
        pet_id=vaccination.pet_id,
        user_id=vaccination.user_id,
        vaccine_name=vaccination.vaccine_name,
        due_on=vaccination.due_on,
        administered_on=vaccination.administered_on,
        is_completed=vaccination.is_completed,
        reminder_days_before=vaccination.reminder_days_before,
        notes=vaccination.notes,
        status=wellness_service.vaccination_status(vaccination),
        created_at=vaccination.created_at,
        updated_at=vaccination.updated_at,
    )


@router.get("/summary", response_model=WellnessSummaryPublic)
async def get_wellness_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WellnessSummaryPublic:
    summary = await wellness_service.get_summary(db, current_user.id)
    return WellnessSummaryPublic.model_validate(summary)


@router.get("/pets/{pet_id}/weights", response_model=PaginatedResponse)
async def list_weight_logs(
    pet_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if not await wellness_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    items, total = await wellness_service.list_weight_logs(db, current_user.id, pet_id, page, page_size)
    return PaginatedResponse(
        items=[WeightLogPublic.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("/pets/{pet_id}/weights", response_model=WeightLogPublic, status_code=status.HTTP_201_CREATED)
async def create_weight_log(
    pet_id: uuid.UUID,
    data: WeightLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightLogPublic:
    if not await wellness_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    entry = await wellness_service.create_weight_log(db, current_user.id, pet_id, data)
    return WeightLogPublic.model_validate(entry)


@router.delete("/weights/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    entry = await wellness_service.get_weight_log_by_id(db, current_user.id, log_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weight log not found")
    await wellness_service.delete_weight_log(db, entry)


@router.get("/pets/{pet_id}/vaccinations", response_model=PaginatedResponse)
async def list_vaccinations(
    pet_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    if not await wellness_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    items, total = await wellness_service.list_vaccinations(db, current_user.id, pet_id, page, page_size)
    return PaginatedResponse(
        items=[_to_vaccination_public(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("/pets/{pet_id}/vaccinations", response_model=VaccinationPublic, status_code=status.HTTP_201_CREATED)
async def create_vaccination(
    pet_id: uuid.UUID,
    data: VaccinationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VaccinationPublic:
    if not await wellness_service.pet_belongs_to_user(db, pet_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")

    vaccination = await wellness_service.create_vaccination(db, current_user.id, pet_id, data)
    return _to_vaccination_public(vaccination)


@router.patch("/vaccinations/{vaccination_id}", response_model=VaccinationPublic)
async def update_vaccination(
    vaccination_id: uuid.UUID,
    data: VaccinationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VaccinationPublic:
    vaccination = await wellness_service.get_vaccination_by_id(db, current_user.id, vaccination_id)
    if not vaccination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaccination record not found")

    updated = await wellness_service.update_vaccination(db, vaccination, data)
    return _to_vaccination_public(updated)


@router.delete("/vaccinations/{vaccination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vaccination(
    vaccination_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    vaccination = await wellness_service.get_vaccination_by_id(db, current_user.id, vaccination_id)
    if not vaccination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaccination record not found")
    await wellness_service.delete_vaccination(db, vaccination)
