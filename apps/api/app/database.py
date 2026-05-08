from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import settings

# Supabase Supavisor (transaction pooler, port 6543) handles connection pooling
# externally, so we use NullPool to avoid double-pooling.
# For non-Supabase setups: use AsyncAdaptedQueuePool with pool_size=5.
_pool_kwargs: dict = (
    {"poolclass": NullPool}
    if settings.is_production
    else {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
