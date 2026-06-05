from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _fake_health_record() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        record_type="diagnosis",
        title="Skin allergy",
        details="Mild dermatitis, continue monitoring.",
        recorded_on=date.today(),
        veterinarian="Dr. Rao",
        clinic_name="City Pet Clinic",
        next_visit_on=date.today(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _fake_medication() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        medication_name="Cetirizine",
        dosage="5mg",
        frequency="once_daily",
        starts_on=date.today(),
        ends_on=None,
        next_due_on=date.today(),
        reminder_days_before=1,
        is_active=True,
        notes="After food",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _fake_expense() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        user_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        category="medicine",
        amount=Decimal("750.00"),
        expense_on=date.today(),
        description="Allergy medication",
        vendor="City Pharmacy",
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_health_records_create_and_list(client: AsyncClient) -> None:
    record = _fake_health_record()

    with (
        patch(
            "app.routers.health_records.health_records_service.pet_belongs_to_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.health_records.health_records_service.create_health_record",
            new_callable=AsyncMock,
            return_value=record,
        ),
        patch(
            "app.routers.health_records.health_records_service.list_health_records",
            new_callable=AsyncMock,
            return_value=([record], 1),
        ),
    ):
        create_response = await client.post(
            f"/api/v1/health-records/pets/{record.pet_id}/records",
            json={
                "record_type": "diagnosis",
                "title": "Skin allergy",
                "details": "Mild dermatitis, continue monitoring.",
                "recorded_on": date.today().isoformat(),
            },
        )
        assert create_response.status_code == 201
        assert create_response.json()["id"] == str(record.id)

        list_response = await client.get(
            f"/api/v1/health-records/pets/{record.pet_id}/records?page=1&page_size=10"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_health_record_update_and_delete(client: AsyncClient) -> None:
    record = _fake_health_record()

    with (
        patch(
            "app.routers.health_records.health_records_service.get_health_record_by_id",
            new_callable=AsyncMock,
            return_value=record,
        ),
        patch(
            "app.routers.health_records.health_records_service.update_health_record",
            new_callable=AsyncMock,
            return_value=record,
        ),
        patch("app.routers.health_records.health_records_service.delete_health_record", new_callable=AsyncMock),
    ):
        update_response = await client.patch(
            f"/api/v1/health-records/records/{record.id}",
            json={"title": "Updated title"},
        )
        assert update_response.status_code == 200

        delete_response = await client.delete(f"/api/v1/health-records/records/{record.id}")
        assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_medications_and_expenses_create_and_list(client: AsyncClient) -> None:
    medication = _fake_medication()
    expense = _fake_expense()

    with (
        patch(
            "app.routers.health_records.health_records_service.pet_belongs_to_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.health_records.health_records_service.create_medication",
            new_callable=AsyncMock,
            return_value=medication,
        ),
        patch(
            "app.routers.health_records.health_records_service.list_medications",
            new_callable=AsyncMock,
            return_value=([medication], 1),
        ),
        patch(
            "app.routers.health_records.health_records_service.create_expense",
            new_callable=AsyncMock,
            return_value=expense,
        ),
        patch(
            "app.routers.health_records.health_records_service.list_expenses",
            new_callable=AsyncMock,
            return_value=([expense], 1),
        ),
    ):
        medication_response = await client.post(
            f"/api/v1/health-records/pets/{medication.pet_id}/medications",
            json={
                "medication_name": "Cetirizine",
                "dosage": "5mg",
                "frequency": "once_daily",
                "starts_on": date.today().isoformat(),
                "next_due_on": date.today().isoformat(),
            },
        )
        assert medication_response.status_code == 201

        medications_list = await client.get(
            f"/api/v1/health-records/pets/{medication.pet_id}/medications?page=1&page_size=10"
        )
        assert medications_list.status_code == 200
        assert medications_list.json()["total"] == 1

        expense_response = await client.post(
            f"/api/v1/health-records/pets/{expense.pet_id}/expenses",
            json={
                "category": "medicine",
                "amount": "750.00",
                "expense_on": date.today().isoformat(),
                "description": "Allergy medication",
            },
        )
        assert expense_response.status_code == 201

        expenses_list = await client.get(
            f"/api/v1/health-records/pets/{expense.pet_id}/expenses?page=1&page_size=10"
        )
        assert expenses_list.status_code == 200
        assert expenses_list.json()["total"] == 1


@pytest.mark.asyncio
async def test_health_summary_and_reminders(client: AsyncClient) -> None:
    summary_payload = {
        "total_records": 3,
        "active_medications": 2,
        "due_medications_7d": 1,
        "upcoming_visits_30d": 1,
        "monthly_expense_total": "2450.00",
        "expense_by_category": [{"category": "food", "total_amount": "1200.00"}],
        "reminders": [
            {
                "item_id": str(uuid.uuid4()),
                "pet_id": str(uuid.uuid4()),
                "pet_name": "Buddy",
                "reminder_type": "medication",
                "title": "Cetirizine (5mg)",
                "due_on": date.today().isoformat(),
                "days_until_due": 0,
                "status": "due_soon",
            }
        ],
    }

    with (
        patch(
            "app.routers.health_records.health_records_service.get_summary",
            new_callable=AsyncMock,
            return_value=summary_payload,
        ),
        patch(
            "app.routers.health_records.health_records_service.get_reminders",
            new_callable=AsyncMock,
            return_value=summary_payload["reminders"],
        ),
    ):
        summary_response = await client.get("/api/v1/health-records/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["active_medications"] == 2

        reminders_response = await client.get("/api/v1/health-records/reminders?window_days=30&limit=20")
        assert reminders_response.status_code == 200
        assert len(reminders_response.json()) == 1
