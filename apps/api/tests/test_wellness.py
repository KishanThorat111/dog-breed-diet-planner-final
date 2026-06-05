from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _fake_weight_log() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        measured_on=date.today(),
        weight_kg=Decimal("22.4"),
        notes="Monthly check",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _fake_vaccination() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        vaccine_name="Rabies",
        due_on=date.today(),
        administered_on=None,
        is_completed=False,
        reminder_days_before=7,
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_list_and_create_weight_logs(client: AsyncClient) -> None:
    log = _fake_weight_log()

    with (
        patch("app.routers.wellness.wellness_service.pet_belongs_to_user", new_callable=AsyncMock, return_value=True),
        patch("app.routers.wellness.wellness_service.list_weight_logs", new_callable=AsyncMock, return_value=([log], 1)),
        patch("app.routers.wellness.wellness_service.create_weight_log", new_callable=AsyncMock, return_value=log),
    ):
        list_response = await client.get(f"/api/v1/wellness/pets/{log.pet_id}/weights?page=1&page_size=10")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        create_response = await client.post(
            f"/api/v1/wellness/pets/{log.pet_id}/weights",
            json={
                "measured_on": date.today().isoformat(),
                "weight_kg": "22.4",
                "notes": "Monthly check",
            },
        )
        assert create_response.status_code == 201
        assert create_response.json()["id"] == str(log.id)


@pytest.mark.asyncio
async def test_delete_weight_log(client: AsyncClient) -> None:
    log = _fake_weight_log()

    with (
        patch("app.routers.wellness.wellness_service.get_weight_log_by_id", new_callable=AsyncMock, return_value=log),
        patch("app.routers.wellness.wellness_service.delete_weight_log", new_callable=AsyncMock),
    ):
        response = await client.delete(f"/api/v1/wellness/weights/{log.id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_and_update_vaccination(client: AsyncClient) -> None:
    vaccination = _fake_vaccination()

    with (
        patch("app.routers.wellness.wellness_service.pet_belongs_to_user", new_callable=AsyncMock, return_value=True),
        patch("app.routers.wellness.wellness_service.create_vaccination", new_callable=AsyncMock, return_value=vaccination),
        patch("app.routers.wellness.wellness_service.get_vaccination_by_id", new_callable=AsyncMock, return_value=vaccination),
        patch("app.routers.wellness.wellness_service.update_vaccination", new_callable=AsyncMock, return_value=vaccination),
        patch("app.routers.wellness.wellness_service.vaccination_status", return_value="due_soon"),
    ):
        create_response = await client.post(
            f"/api/v1/wellness/pets/{vaccination.pet_id}/vaccinations",
            json={
                "vaccine_name": "Rabies",
                "due_on": date.today().isoformat(),
                "is_completed": False,
            },
        )
        assert create_response.status_code == 201
        assert create_response.json()["status"] == "due_soon"

        update_response = await client.patch(
            f"/api/v1/wellness/vaccinations/{vaccination.id}",
            json={"is_completed": True, "administered_on": date.today().isoformat()},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "due_soon"


@pytest.mark.asyncio
async def test_wellness_summary(client: AsyncClient) -> None:
    summary_payload = {
        "total_pets": 2,
        "pets_with_weight_logs": 1,
        "upcoming_vaccinations": 2,
        "overdue_vaccinations": 1,
        "pet_trends": [
            {
                "pet_id": str(uuid.uuid4()),
                "pet_name": "Buddy",
                "latest_weight_kg": "20.5",
                "previous_weight_kg": "20.0",
                "delta_kg": "0.5",
                "trend": "up",
            }
        ],
        "reminders": [
            {
                "vaccination_id": str(uuid.uuid4()),
                "pet_id": str(uuid.uuid4()),
                "pet_name": "Buddy",
                "vaccine_name": "DHPP",
                "due_on": date.today().isoformat(),
                "days_until_due": 0,
                "status": "due_soon",
            }
        ],
    }

    with patch("app.routers.wellness.wellness_service.get_summary", new_callable=AsyncMock, return_value=summary_payload):
        response = await client.get("/api/v1/wellness/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_pets"] == 2
    assert body["upcoming_vaccinations"] == 2
    assert body["pet_trends"][0]["trend"] == "up"
