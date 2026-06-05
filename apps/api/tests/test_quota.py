from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.middleware.auth import ANONYMOUS_USER_ID
from app.models.ai_usage import AIUsage
from app.models.subscription import Subscription
from app.models.user import User
from app.services.quota_service import quota_service


@pytest.mark.asyncio
async def test_guest_quota_limit_enforced(db_session) -> None:
    anon_user = User(
        id=ANONYMOUS_USER_ID,
        email="anonymous@dietpaw.local",
        password_hash="!anonymous!",
        full_name="Anonymous",
        is_active=True,
    )
    db_session.add(anon_user)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    for _ in range(25):
        db_session.add(
            AIUsage(
                user_id=ANONYMOUS_USER_ID,
                provider="gemini-vision",
                model="gemini-2.5-flash",
                prompt_tokens=10,
                completion_tokens=10,
                caller="vision_classify",
                created_at=now - timedelta(minutes=5),
            )
        )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await quota_service.assert_can_use_ai(db_session, ANONYMOUS_USER_ID)

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_user_with_zero_credits_is_blocked_after_trial(db_session) -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"quota-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Quota User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        Subscription(
            user_id=user_id,
            plan="free",
            status="active",
            credits_remaining=0,
            trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await quota_service.assert_can_use_ai(db_session, user_id)

    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_user_in_trial_can_use_ai(db_session) -> None:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"trial-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        full_name="Trial User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        Subscription(
            user_id=user_id,
            plan="free",
            status="active",
            credits_remaining=0,
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    await db_session.commit()

    await quota_service.assert_can_use_ai(db_session, user_id)
