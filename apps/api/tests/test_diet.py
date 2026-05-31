"""Tests for anonymous diet plan endpoints."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_diet_plan(client: AsyncClient) -> None:
  response = await client.post(
    "/api/v1/diet-plans/generate",
    json={
      "breed": "labrador_retriever",
      "age_months": 36,
      "weight_kg": "30.0",
      "activity_level": "active",
      "is_neutered": True,
      "sex": "male",
    },
  )

  assert response.status_code == 201, response.text
  body = response.json()
  assert body["breed"] == "labrador_retriever"
  assert body["activity_level"] == "active"
  assert body["daily_calories"] > 0
  assert len(body["food_recommendations"]) > 0
  assert len(body["feeding_schedule"]) > 0


@pytest.mark.asyncio
async def test_list_diet_plans_returns_empty_pagination(client: AsyncClient) -> None:
  response = await client.get("/api/v1/diet-plans?page=1&page_size=10")
  assert response.status_code == 200
  body = response.json()
  assert body["items"] == []
  assert body["total"] == 0
  assert body["page"] == 1
  assert body["page_size"] == 10


@pytest.mark.asyncio
async def test_get_diet_plan_not_persisted(client: AsyncClient) -> None:
  response = await client.get(f"/api/v1/diet-plans/{uuid.uuid4()}")
  assert response.status_code == 404
  assert "not persisted" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_diet_plan_validation(client: AsyncClient) -> None:
  response = await client.post(
    "/api/v1/diet-plans/generate",
    json={
      "age_months": 999,
      "weight_kg": "10.0",
    },
  )
  assert response.status_code == 422
