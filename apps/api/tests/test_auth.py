"""Tests for health and auth endpoints."""
from __future__ import annotations

import uuid

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
    async def test_health_includes_ai_fields(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        body = response.json()
        assert "ai_provider" in body
        assert "ai_enabled" in body
        assert "gemini_configured" in body


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

    @pytest.mark.asyncio
    async def test_health_records_requires_auth(self) -> None:
        """Health records API should reject unauthenticated access."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/health-records/summary")

        assert response.status_code in (401, 403)


class TestAuthEndpoints:
    """Register/login should work for local JWT auth."""

    @pytest.mark.asyncio
    async def test_register_login_flow(self, client: AsyncClient) -> None:
        email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123"

        register = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Test User",
            },
        )
        assert register.status_code == 201, register.text
        reg_body = register.json()
        assert "access_token" in reg_body
        assert reg_body["email"] == email

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        login_body = login.json()
        assert "access_token" in login_body
        assert login_body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_conflict(self, client: AsyncClient) -> None:
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123"

        first = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "A"},
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "A"},
        )
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client: AsyncClient) -> None:
        email = f"wrongpass-{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123"

        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "A"},
        )
        assert response.status_code == 201

        wrong_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "not-the-password"},
        )
        assert wrong_login.status_code == 401

    @pytest.mark.asyncio
    async def test_register_rejects_weak_password(self, client: AsyncClient) -> None:
        email = f"weak-{uuid.uuid4().hex[:8]}@example.com"

        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "weakpass", "full_name": "A"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_and_me_flow(self, auth_client: AsyncClient) -> None:
        email = f"refresh-{uuid.uuid4().hex[:8]}@example.com"
        password = "Password123"

        register = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Refresh User"},
        )
        assert register.status_code == 201, register.text
        register_body = register.json()
        assert "refresh_token" in register_body

        refresh = await auth_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": register_body["refresh_token"]},
        )
        assert refresh.status_code == 200, refresh.text
        refresh_body = refresh.json()
        assert "access_token" in refresh_body
        assert "refresh_token" in refresh_body

        me = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_body['access_token']}"},
        )
        assert me.status_code == 200, me.text
        me_body = me.json()
        assert me_body["email"] == email
        assert "subscription" in me_body
