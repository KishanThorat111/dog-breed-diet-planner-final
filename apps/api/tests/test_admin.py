"""
Tests for admin-only endpoints.
Verifies that standard users are forbidden and admin users have access.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAdminStats:
    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, client: AsyncClient) -> None:
        """Regular users must get 403 on admin endpoints."""
        response = await client.get("/api/v1/admin/stats")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_access_stats(self, admin_client: AsyncClient) -> None:
        """Admin users must receive stats (200) or at worst a DB error (500), not 403."""
        response = await admin_client.get("/api/v1/admin/stats")
        assert response.status_code != 403, "Admin user should not be forbidden"

    @pytest.mark.asyncio
    async def test_admin_users_list(self, admin_client: AsyncClient) -> None:
        response = await admin_client.get("/api/v1/admin/users")
        assert response.status_code not in (401, 403)

    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_users(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 403


class TestAdminAI:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_read_ai_config(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/ai/config")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_read_ai_config(self, admin_client: AsyncClient) -> None:
        response = await admin_client.get("/api/v1/admin/ai/config")
        assert response.status_code == 200
        body = response.json()
        assert "providers" in body

    @pytest.mark.asyncio
    async def test_admin_ai_health_endpoint(self, admin_client: AsyncClient) -> None:
        response = await admin_client.get("/api/v1/admin/ai/health")
        assert response.status_code == 200
        body = response.json()
        assert "results" in body

    @pytest.mark.asyncio
    async def test_admin_can_set_supported_gemini_fallback_model(self, admin_client: AsyncClient) -> None:
        response = await admin_client.put(
            "/api/v1/admin/ai/config",
            json={
                "active_model": "gemini-2.5-flash",
                "fallback_models": ["gemini-2.5-flash-lite"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["active_model"] == "gemini-2.5-flash"
        assert "gemini-2.5-flash-lite" in body.get("fallback_models", [])

    @pytest.mark.asyncio
    async def test_admin_cannot_set_shutdown_gemini_models(self, admin_client: AsyncClient) -> None:
        response = await admin_client.put(
            "/api/v1/admin/ai/config",
            json={"active_model": "gemini-2.0-flash"},
        )
        assert response.status_code == 422
