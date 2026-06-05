from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(auth_client: AsyncClient) -> dict[str, str]:
    email = f"reports-{uuid.uuid4().hex[:8]}@example.com"
    password = "Password123"

    register = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Reports User"},
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_download_diet_report_pdf_supports_current_and_legacy_routes(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    pet_response = await auth_client.post(
        "/api/v1/pets",
        headers=headers,
        json={
            "name": "Rex",
            "breed": "thai_ridgeback",
            "age_months": 30,
            "weight_kg": "24.0",
            "activity_level": "active",
            "sex": "male",
        },
    )
    assert pet_response.status_code == 201, pet_response.text
    pet_id = pet_response.json()["id"]

    plan_response = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={
            "pet_id": pet_id,
            "breed": "thai_ridgeback",
            "age_months": 30,
            "weight_kg": "24.0",
            "activity_level": "active",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan_id = plan_response.json()["id"]

    current_route = await auth_client.get(
        f"/api/v1/reports/diet-plan/{plan_id}/pdf",
        headers=headers,
    )
    assert current_route.status_code == 200, current_route.text
    assert current_route.headers.get("content-type", "").startswith("application/pdf")
    assert current_route.content.startswith(b"%PDF")

    legacy_route = await auth_client.get(
        f"/api/v1/reports/{pet_id}/diet-plan/{plan_id}/pdf",
        headers=headers,
    )
    assert legacy_route.status_code == 200, legacy_route.text
    assert legacy_route.headers.get("content-type", "").startswith("application/pdf")


@pytest.mark.asyncio
async def test_multiple_diet_generations_create_distinct_saved_reports(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    pet_response = await auth_client.post(
        "/api/v1/pets",
        headers=headers,
        json={
            "name": "Bolt",
            "breed": "mixed_breed",
            "age_months": 20,
            "weight_kg": "18.5",
            "activity_level": "moderate",
            "sex": "male",
        },
    )
    assert pet_response.status_code == 201, pet_response.text
    pet_id = pet_response.json()["id"]

    first = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={
            "pet_id": pet_id,
            "breed": "labrador_retriever",
            "age_months": 20,
            "weight_kg": "18.5",
            "activity_level": "moderate",
        },
    )
    assert first.status_code == 201, first.text

    second = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={
            "pet_id": pet_id,
            "breed": "thai_ridgeback",
            "age_months": 20,
            "weight_kg": "18.5",
            "activity_level": "moderate",
        },
    )
    assert second.status_code == 201, second.text

    assert first.json()["id"] != second.json()["id"]

    listed = await auth_client.get(f"/api/v1/diet-plans?pet_id={pet_id}", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 2

    plan_ids = {item["id"] for item in body["items"]}
    assert first.json()["id"] in plan_ids
    assert second.json()["id"] in plan_ids

    breeds = {item["breed"] for item in body["items"]}
    assert "labrador_retriever" in breeds
    assert "thai_ridgeback" in breeds
