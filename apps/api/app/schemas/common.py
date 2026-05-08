from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class APIBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedResponse(APIBaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(APIBaseModel):
    message: str


class IDResponse(APIBaseModel):
    id: uuid.UUID
