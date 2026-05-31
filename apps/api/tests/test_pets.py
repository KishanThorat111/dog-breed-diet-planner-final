"""Tests for pet CRUD API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _fake_pet(name: str = "Buddy") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        name=name,
        breed="golden_retriever",
        age_months=24,
        weight_kg=Decimal("30.5"),
        sex="male",
        is_neutered=True,
        life_stage="adult",
        activity_level="active",
        allergies=[],
        health_conditions=[],
        notes=None,
        avatar_url=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_pet(client: AsyncClient) -> None:
    with patch("app.services.pet_service.pet_service.create", new_callable=AsyncMock, return_value=_fake_pet("Buddy")):
        response = await client.post(
            "/api/v1/pets",
            json={
                "name": "Buddy",
                "breed": "golden_retriever",
                "age_months": 24,
                "weight_kg": "30.5",
                "sex": "male",
                "is_neutered": True,
                "activity_level": "active",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Buddy"
    assert data["breed"] == "golden_retriever"
    assert data["activity_level"] in ("active", "moderate", "light", "sedentary", "very_active")
    assert "id" in data


@pytest.mark.asyncio
async def test_list_pets(client: AsyncClient) -> None:
    with patch(
        "app.services.pet_service.pet_service.list_by_user",
        new_callable=AsyncMock,
        return_value=([_fake_pet("Max")], 1),
    ):
        response = await client.get("/api/v1/pets")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_nonexistent_pet(client: AsyncClient) -> None:
    with patch("app.services.pet_service.pet_service.get_by_id", new_callable=AsyncMock, return_value=None):
        response = await client.get("/api/v1/pets/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_pet(client: AsyncClient) -> None:
    pet = _fake_pet("Luna")
    updated = _fake_pet("Luna Updated")
    updated.id = pet.id

    with (
        patch("app.services.pet_service.pet_service.get_by_id", new_callable=AsyncMock, return_value=pet),
        patch("app.services.pet_service.pet_service.update", new_callable=AsyncMock, return_value=updated),
    ):
        update_response = await client.patch(
            f"/api/v1/pets/{pet.id}", json={"name": "Luna Updated", "weight_kg": "8.5"}
        )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Luna Updated"


@pytest.mark.asyncio
async def test_delete_pet(client: AsyncClient) -> None:
    pet = _fake_pet("Temp Pet")
    with (
        patch(
            "app.services.pet_service.pet_service.get_by_id",
            new_callable=AsyncMock,
            side_effect=[pet, None],
        ),
        patch("app.services.pet_service.pet_service.soft_delete", new_callable=AsyncMock),
    ):
        delete_response = await client.delete(f"/api/v1/pets/{pet.id}")
        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/v1/pets/{pet.id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pet_validation_invalid_activity(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/pets", json={"name": "Test", "activity_level": "invalid_level"}
    )
    assert response.status_code == 422
