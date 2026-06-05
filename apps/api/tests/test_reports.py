from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.pet import Pet
from app.models.prediction import AIPrediction


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


@pytest.mark.asyncio
async def test_generate_without_pet_id_persists_plan_creates_pet_and_downloads_pdf(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    plan_response = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={
            "pet_name": "Thai Ridgeback",
            "breed": "thai_ridgeback",
            "age_months": 26,
            "weight_kg": "22.0",
            "activity_level": "active",
            "sex": "male",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()

    assert plan["breed"] == "thai_ridgeback"
    assert plan["pet_id"]
    assert plan["user_id"] != "00000000-0000-0000-0000-000000000001"

    pet_response = await auth_client.get(f"/api/v1/pets/{plan['pet_id']}", headers=headers)
    assert pet_response.status_code == 200, pet_response.text
    pet = pet_response.json()
    assert pet["name"] == "Thai Ridgeback"
    assert pet["breed"] == "thai_ridgeback"

    report_response = await auth_client.get(
        f"/api/v1/reports/diet-plan/{plan['id']}/pdf",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    assert report_response.headers.get("content-type", "").startswith("application/pdf")
    assert report_response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_generate_with_long_pet_name_is_sanitized_and_report_downloads(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    very_long_name = "Thai Ridgeback " * 20
    plan_response = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={
            "pet_name": very_long_name,
            "breed": "thai_ridgeback",
            "age_months": 24,
            "weight_kg": "20.0",
            "activity_level": "active",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()

    pet_response = await auth_client.get(f"/api/v1/pets/{plan['pet_id']}", headers=headers)
    assert pet_response.status_code == 200, pet_response.text
    pet = pet_response.json()
    assert len(pet["name"]) <= 100
    assert pet["name"]

    report_response = await auth_client.get(
        f"/api/v1/reports/diet-plan/{plan['id']}/pdf",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    disposition = report_response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "filename=" in disposition


@pytest.mark.asyncio
async def test_report_download_handles_non_ascii_pet_names(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    pet_response = await auth_client.post(
        "/api/v1/pets",
        headers=headers,
        json={
            "name": "Milo🐾",
            "breed": "mixed_breed",
            "age_months": 18,
            "weight_kg": "12.0",
            "activity_level": "moderate",
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
            "breed": "mixed_breed",
            "age_months": 18,
            "weight_kg": "12.0",
            "activity_level": "moderate",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan_id = plan_response.json()["id"]

    report_response = await auth_client.get(
        f"/api/v1/reports/diet-plan/{plan_id}/pdf",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    assert report_response.headers.get("content-type", "").startswith("application/pdf")


@pytest.mark.asyncio
async def test_diet_generation_handles_legacy_malformed_pet_data(auth_client: AsyncClient, db_session) -> None:
    headers = await _register_and_auth_headers(auth_client)

    # Register a user and create a malformed legacy pet row directly.
    register = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"legacy-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123",
            "full_name": "Legacy User",
        },
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    user_id = uuid.UUID(register.json()["user_id"])
    legacy_headers = {"Authorization": f"Bearer {token}"}

    legacy_pet = Pet(
        user_id=user_id,
        name="Legacy Dog",
        breed="Thai Ridgeback ###",
        age_months=-5,
        weight_kg=Decimal("-12.0"),
        sex="unknown",
        is_neutered=False,
        life_stage="adult",
        activity_level="extreme_hyper",
        allergies=["Chicken", 42, None],
        health_conditions="arthritis, obese",
        notes=None,
    )
    db_session.add(legacy_pet)
    await db_session.commit()
    await db_session.refresh(legacy_pet)

    response = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=legacy_headers,
        json={"pet_id": str(legacy_pet.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["daily_calories"] > 0
    assert body["activity_level"] in {"moderate", "active", "light", "sedentary", "very_active"}


@pytest.mark.asyncio
async def test_report_download_works_for_soft_deleted_pet(auth_client: AsyncClient) -> None:
    headers = await _register_and_auth_headers(auth_client)

    pet_response = await auth_client.post(
        "/api/v1/pets",
        headers=headers,
        json={
            "name": "Deleted Later",
            "breed": "mixed_breed",
            "age_months": 16,
            "weight_kg": "13.0",
            "activity_level": "moderate",
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
            "breed": "mixed_breed",
            "age_months": 16,
            "weight_kg": "13.0",
            "activity_level": "moderate",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan_id = plan_response.json()["id"]

    delete_response = await auth_client.delete(f"/api/v1/pets/{pet_id}", headers=headers)
    assert delete_response.status_code == 204, delete_response.text

    report_response = await auth_client.get(
        f"/api/v1/reports/diet-plan/{plan_id}/pdf",
        headers=headers,
    )
    assert report_response.status_code == 200, report_response.text
    assert report_response.headers.get("content-type", "").startswith("application/pdf")


@pytest.mark.asyncio
async def test_generate_from_prediction_uses_highest_confidence_recommendation(
    auth_client: AsyncClient,
    db_session,
) -> None:
    register = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"prediction-{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123",
            "full_name": "Prediction User",
        },
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    user_id = uuid.UUID(register.json()["user_id"])
    headers = {"Authorization": f"Bearer {token}"}

    prediction = AIPrediction(
        user_id=user_id,
        pet_id=None,
        upload_id=None,
        top_breed="mixed_breed",
        top_confidence=Decimal("0.10"),
        all_predictions=[
            {"breed": "mixed_breed", "display_name": "Mixed Breed", "confidence": 0.10},
            {"breed": "german_shepherd", "display_name": "German Shepherd", "confidence": 0.99},
        ],
        model_version="gemini-vision",
        inference_time_ms=11,
    )
    db_session.add(prediction)
    await db_session.commit()
    await db_session.refresh(prediction)

    response = await auth_client.post(
        "/api/v1/diet-plans/generate",
        headers=headers,
        json={"prediction_id": str(prediction.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["breed"] == "german_shepherd"

    pet_response = await auth_client.get(f"/api/v1/pets/{body['pet_id']}", headers=headers)
    assert pet_response.status_code == 200, pet_response.text
    assert pet_response.json()["breed"] == "german_shepherd"
