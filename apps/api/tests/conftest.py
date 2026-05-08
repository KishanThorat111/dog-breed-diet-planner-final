"""Shared test fixtures and configuration."""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.user import User

# -------------------------------------------------------------------------
# Database
# -------------------------------------------------------------------------
# Unit tests: in-memory SQLite (no JSONB support — integration tests need PG)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Opt-in integration tests against real PG (must set TEST_DATABASE_URL env var)
import os
_INTEGRATION_DB_URL = os.getenv("TEST_DATABASE_URL", "")


def pytest_configure(config):  # type: ignore[no-untyped-def]
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: requires a real PostgreSQL database")


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# -------------------------------------------------------------------------
# Auth helpers
# -------------------------------------------------------------------------
_FIXED_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_FIXED_ADMIN_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def make_mock_user(is_admin: bool = False) -> User:
    return User(
        id=_FIXED_ADMIN_ID if is_admin else _FIXED_USER_ID,
        password_hash="hashed_test_password",
        email="admin@test.com" if is_admin else "test@example.com",
        full_name="Admin User" if is_admin else "Test User",
        is_admin=is_admin,
        is_active=True,
    )


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    from app.middleware.auth import get_current_user, require_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: make_mock_user(is_admin=False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client authenticated as an admin user."""
    async def override_get_db():
        yield db_session

    from app.middleware.auth import get_current_user, require_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: make_mock_user(is_admin=True)
    app.dependency_overrides[require_admin] = lambda: make_mock_user(is_admin=True)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return _FIXED_USER_ID


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    return _FIXED_ADMIN_ID
