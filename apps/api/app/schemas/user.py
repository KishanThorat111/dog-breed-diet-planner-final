from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr

from app.schemas.common import APIBaseModel


class UserPublic(APIBaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    is_admin: bool
    created_at: datetime


class UserUpdate(APIBaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class ClerkWebhookUserData(APIBaseModel):
    id: str
    email_addresses: list[dict]
    first_name: str | None = None
    last_name: str | None = None
    image_url: str | None = None

    @property
    def primary_email(self) -> str | None:
        for ea in self.email_addresses:
            if ea.get("id") == self.model_extra.get("primary_email_address_id"):
                return ea.get("email_address")
        if self.email_addresses:
            return self.email_addresses[0].get("email_address")
        return None

    @property
    def display_name(self) -> str | None:
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else None
