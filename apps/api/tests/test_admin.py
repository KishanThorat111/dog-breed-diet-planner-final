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


class TestAdminPredictions:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_list_all_predictions(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/admin/predictions")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_list_all_predictions(self, admin_client: AsyncClient) -> None:
        response = await admin_client.get("/api/v1/admin/predictions")
        assert response.status_code != 403
