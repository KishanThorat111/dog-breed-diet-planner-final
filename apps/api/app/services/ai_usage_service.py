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

    # After recording, attempt to deduct credits if applicable
    if user_id is None:
        return

    try:
        from datetime import timezone
        from sqlalchemy import select
        from app.models.subscription import Subscription

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            sub = (await session.execute(select(Subscription).where(Subscription.user_id == user_id))).scalar_one_or_none()
            if not sub:
                return

            # If trial active, do not deduct
            if sub.trial_ends_at and sub.trial_ends_at > now:
                return

            # Deduct tokens (policy: 1 credit per 100 tokens, round up)
            total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
            if total_tokens <= 0:
                return

            credits_to_deduct = (total_tokens + 99) // 100
            sub.credits_remaining = max(0, (sub.credits_remaining or 0) - credits_to_deduct)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
    except Exception:
        # Non-fatal: usage recording should not break caller
        return


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
