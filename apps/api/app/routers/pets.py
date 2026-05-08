from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.pet import PetCreate, PetPublic, PetUpdate
from app.services.pet_service import pet_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_pets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    pets, total = await pet_service.list_by_user(db, current_user.id, page, page_size)
    return PaginatedResponse(
        items=[PetPublic.model_validate(p) for p in pets],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=PetPublic, status_code=status.HTTP_201_CREATED)
async def create_pet(
    data: PetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PetPublic:
    pet = await pet_service.create(db, current_user.id, data)
    return PetPublic.model_validate(pet)


@router.get("/{pet_id}", response_model=PetPublic)
async def get_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PetPublic:
    pet = await pet_service.get_by_id(db, pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return PetPublic.model_validate(pet)


@router.patch("/{pet_id}", response_model=PetPublic)
async def update_pet(
    pet_id: uuid.UUID,
    data: PetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PetPublic:
    pet = await pet_service.get_by_id(db, pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    updated = await pet_service.update(db, pet, data)
    return PetPublic.model_validate(updated)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    pet = await pet_service.get_by_id(db, pet_id, current_user.id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    await pet_service.soft_delete(db, pet)
