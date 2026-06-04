import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.user import User
from app.models.subscription import Subscription
from app.services.ai_usage_service import record_usage


@pytest.mark.asyncio
async def test_credit_deduction(db_session):
    # create user
    user = User(
        id=uuid.UUID("9a9a9a9a-9a9a-9a9a-9a9a-9a9a9a9a9a9a"),
        email="billing@test",
        password_hash="x",
        full_name="Bill Tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # create subscription with credits
    sub = Subscription(user_id=user.id, plan="free", credits_remaining=10)
    db_session.add(sub)
    await db_session.commit()

    # Record usage: 150 tokens -> should deduct 2 credits (1 per 100 tokens)
    await record_usage(
        user_id=user.id,
        provider="test",
        model="m",
        prompt_tokens=50,
        completion_tokens=100,
        caller="test",
        session=db_session,
    )

    result = await db_session.execute(select(Subscription).where(Subscription.user_id == user.id))
    updated = result.scalar_one()
    assert updated.credits_remaining == 8
