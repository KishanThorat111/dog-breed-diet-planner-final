"""
In-memory cache — no Redis required.
Simple TTL dict. Good enough for a single-process deployment.
If you need persistence or multi-instance caching, swap in Redis later.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        self._store[key] = (value, time.monotonic() + ttl_seconds)
        return True

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass  # Nothing to close


# Module-level singleton
cache = Cache()
