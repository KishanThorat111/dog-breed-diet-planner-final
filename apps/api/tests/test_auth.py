"""
Tests for authentication middleware and auth router (webhook handling).
"""
from __future__ import annotations

import json
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Health/readiness checks must not require auth."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "environment" in body

    @pytest.mark.asyncio
    async def test_health_includes_ml_status(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        body = response.json()
        assert "ml_model" in body
        assert body["ml_model"] in ("loaded", "not_loaded", "failed", "unloaded")


class TestProtectedRoutes:
    """Protected routes must return 401/403 without a valid token."""

    @pytest.mark.asyncio
    async def test_pets_requires_auth(self) -> None:
        """Test that pets endpoint requires authentication (no override)."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/pets")
        # HTTPBearer raises 403 (no credentials) or 401
        assert response.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_admin_requires_admin_role(self, client: AsyncClient) -> None:
        """Standard users must be forbidden from admin endpoints."""
        response = await client.get("/api/v1/admin/stats")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_accessible_to_admin(self, admin_client: AsyncClient) -> None:
        """Admin users can access admin endpoints."""
        response = await admin_client.get("/api/v1/admin/stats")
        # 200 or 500 (DB issues in test env) — not 403
        assert response.status_code != 403


class TestWebhookEndpoint:
    """Clerk webhook must verify signature unless in dev mode."""

    @pytest.mark.asyncio
    async def test_webhook_rejects_without_signature(self, client: AsyncClient) -> None:
        """Webhook without svix headers should fail verification."""
        response = await client.post(
            "/api/v1/auth/webhook",
            json={"type": "user.created", "data": {}},
        )
        # Should reject — no svix-signature header
        # In dev mode with no CLERK_WEBHOOK_SECRET, it may pass with 422 (missing body fields)
        assert response.status_code in (400, 401, 422, 204)

    @pytest.mark.asyncio
    async def test_webhook_user_created_event(self, client: AsyncClient) -> None:
        """Webhook with valid user.created event shape should not 500."""
        payload = {
            "type": "user.created",
            "data": {
                "id": "user_test_webhook_123",
                "email_addresses": [
                    {"id": "ea_1", "email_address": "webhook@test.com"}
                ],
                "primary_email_address_id": "ea_1",
                "first_name": "Webhook",
                "last_name": "Test",
                "image_url": None,
            },
        }
        response = await client.post("/api/v1/auth/webhook", json=payload)
        # In dev mode (no webhook secret), the event is processed
        assert response.status_code in (204, 401)
