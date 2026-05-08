"""Tests for pet CRUD API endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_pet(client: AsyncClient) -> None:
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
    assert data["activity_level"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_pets(client: AsyncClient) -> None:
    # Create a pet first
    await client.post("/api/v1/pets", json={"name": "Max", "activity_level": "moderate"})

    response = await client.get("/api/v1/pets")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_nonexistent_pet(client: AsyncClient) -> None:
    response = await client.get("/api/v1/pets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_pet(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/pets", json={"name": "Luna", "activity_level": "light"}
    )
    pet_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/pets/{pet_id}", json={"name": "Luna Updated", "weight_kg": "8.5"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Luna Updated"


@pytest.mark.asyncio
async def test_delete_pet(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/pets", json={"name": "Temp Pet", "activity_level": "moderate"}
    )
    pet_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/pets/{pet_id}")
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = await client.get(f"/api/v1/pets/{pet_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pet_validation_invalid_activity(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/pets", json={"name": "Test", "activity_level": "invalid_level"}
    )
    assert response.status_code == 422
