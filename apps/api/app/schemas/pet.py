from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIBaseModel

ACTIVITY_LEVELS = ("sedentary", "light", "moderate", "active", "very_active")
LIFE_STAGES = ("puppy", "adult", "senior")

# Frontend sends compound values; we normalise them into sex + is_neutered
_SEX_MAP: dict[str, tuple[str, bool]] = {
    "male": ("male", False),
    "female": ("female", False),
    "male_neutered": ("male", True),
    "female_spayed": ("female", True),
    "male_intact": ("male", False),
    "female_intact": ("female", False),
}


class PetCreate(APIBaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    breed: str | None = None
    age_months: Annotated[int | None, Field(ge=0, le=360)] = None
    weight_kg: Annotated[Decimal | None, Field(ge=Decimal("0.1"), le=Decimal("200"))] = None
    # Accepts: male | female | male_neutered | female_spayed
    sex: str | None = None
    is_neutered: bool = False
    life_stage: str = "adult"
    activity_level: str = "moderate"
    allergies: list[str] = []
    health_conditions: list[str] = []
    notes: str | None = None
    avatar_url: str | None = None

    @field_validator("activity_level")
    @classmethod
    def validate_activity_level(cls, v: str) -> str:
        if v not in ACTIVITY_LEVELS:
            raise ValueError(f"activity_level must be one of: {', '.join(ACTIVITY_LEVELS)}")
        return v

    @field_validator("life_stage")
    @classmethod
    def validate_life_stage(cls, v: str) -> str:
        if v not in LIFE_STAGES:
            raise ValueError(f"life_stage must be one of: {', '.join(LIFE_STAGES)}")
        return v

    @model_validator(mode="after")
    def normalise_sex(self) -> "PetCreate":
        """Split frontend compound sex values (male_neutered) into sex + is_neutered."""
        if self.sex and self.sex in _SEX_MAP:
            self.sex, self.is_neutered = _SEX_MAP[self.sex]
        elif self.sex and self.sex not in ("male", "female", None):
            raise ValueError(f"sex must be one of: {', '.join(_SEX_MAP)}")
        return self


class PetUpdate(APIBaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=100)] = None
    breed: str | None = None
    age_months: Annotated[int | None, Field(ge=0, le=360)] = None
    weight_kg: Annotated[Decimal | None, Field(ge=Decimal("0.1"), le=Decimal("200"))] = None
    sex: str | None = None
    is_neutered: bool | None = None
    life_stage: str | None = None
    activity_level: str | None = None
    allergies: list[str] | None = None
    health_conditions: list[str] | None = None
    notes: str | None = None
    avatar_url: str | None = None

    @model_validator(mode="after")
    def normalise_sex(self) -> "PetUpdate":
        if self.sex and self.sex in _SEX_MAP:
            self.sex, neutered = _SEX_MAP[self.sex]
            if self.is_neutered is None:
                self.is_neutered = neutered
        return self


class PetPublic(APIBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    breed: str | None
    age_months: int | None
    weight_kg: Decimal | None
    sex: str | None
    is_neutered: bool
    life_stage: str
    activity_level: str
    allergies: list[str]
    health_conditions: list[str]
    notes: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
