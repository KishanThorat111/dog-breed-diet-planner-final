from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.middleware.auth import ANONYMOUS_USER_ID
from app.models.ai_usage import AIUsage
from app.models.subscription import Subscription


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class QuotaService:
    async def ensure_subscription(self, db: AsyncSession, user_id: uuid.UUID) -> Subscription:
        sub = (
            await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        ).scalar_one_or_none()
        if sub:
            return sub

        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user_id,
            plan="free",
            status="active",
            credits_remaining=settings.free_plan_initial_credits,
            trial_ends_at=now + timedelta(days=settings.trial_duration_days),
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    async def _guest_usage_last_24h(self, db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)
        result = await db.execute(
            select(func.count())
            .select_from(AIUsage)
            .where(AIUsage.user_id == ANONYMOUS_USER_ID, AIUsage.created_at >= since)
        )
        return int(result.scalar_one() or 0)

    async def assert_can_use_ai(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        if user_id == ANONYMOUS_USER_ID:
            used = await self._guest_usage_last_24h(db)
            if used >= settings.guest_ai_daily_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Guest AI usage limit reached. Please sign up or log in to continue."
                    ),
                )
            return

        sub = await self.ensure_subscription(db, user_id)
        now = datetime.now(timezone.utc)
        trial_ends_at = _normalize_utc(sub.trial_ends_at)

        if trial_ends_at and trial_ends_at > now:
            return

        if (sub.credits_remaining or 0) > 0:
            return

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No AI credits remaining. Please top up credits to continue.",
        )

    async def can_use_ai(self, db: AsyncSession, user_id: uuid.UUID) -> bool:
        try:
            await self.assert_can_use_ai(db, user_id)
            return True
        except HTTPException:
            return False


quota_service = QuotaService()
