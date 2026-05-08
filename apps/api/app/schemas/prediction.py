from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.common import APIBaseModel


class BreedPrediction(APIBaseModel):
    breed: str
    confidence: float
    display_name: str


class PredictionPublic(APIBaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    pet_id: uuid.UUID | None
    top_breed: str
    top_confidence: Decimal
    all_predictions: list[BreedPrediction]
    model_version: str
    inference_time_ms: int | None
    image_url: str | None = None
    created_at: datetime


class AnalyzeRequest(APIBaseModel):
    pet_id: uuid.UUID | None = None
    # Image comes as multipart form file, not in this schema
