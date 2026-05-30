from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import settings

# Use NullPool only for Supabase transaction pooler URLs.
# For local or self-managed Postgres, keep a small SQLAlchemy queue pool.
_db_url = settings.database_url.lower()
_is_supabase_pooler = "pooler.supabase.com" in _db_url

if _is_supabase_pooler:
    _pool_kwargs: dict = {"poolclass": NullPool}
else:
    _pool_kwargs = {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

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
