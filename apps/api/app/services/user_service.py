from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    # -- Password helpers ----------------------------------------------------

    def hash_password(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

    # -- Queries -------------------------------------------------------------

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email.lower().strip(), User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    # -- Mutations ------------------------------------------------------------

    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            password_hash=self.hash_password(password),
            full_name=full_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created user email=%s", user.email)
        return user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> User | None:
        """Return the user if email + password are valid, else None."""
        user = await self.get_by_email(db, email)
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    async def soft_delete(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await self.get_by_id(db, user_id)
        if user:
            user.deleted_at = datetime.now(timezone.utc)
            user.is_active = False
            await db.commit()
            logger.info("Soft-deleted user id=%s", user_id)

    async def list_users(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        from sqlalchemy import func

        count_result = await db.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total  # type: ignore[return-value]


user_service = UserService()
