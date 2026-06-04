from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from app.database import AsyncSessionLocal
from app.models.ai_usage import AIUsage


async def record_usage(
    *,
    user_id: uuid.UUID | None,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    caller: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> None:
    """Persist AI usage to the database. Runs in its own session so callers needn't pass one."""
    async with AsyncSessionLocal() as session:
        usage = AIUsage(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            caller=caller,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        session.add(usage)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# helper to schedule fire-and-forget recording from sync contexts
def schedule_record(*args, **kwargs):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(record_usage(*args, **kwargs))
    else:
        # run in new loop
        asyncio.run(record_usage(*args, **kwargs))
