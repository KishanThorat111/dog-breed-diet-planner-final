from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import limiter
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.prediction import PredictionPublic, BreedPrediction

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/analyze", response_model=PredictionPublic)
@limiter.limit("10/minute")
async def analyze_image(
    request: Request,
    file: UploadFile = File(..., description="Dog image (JPEG, PNG, or WEBP, max 10MB)"),
    pet_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictionPublic:
    """
    Upload a dog image and receive AI breed identification.
    Rate limited to 10 requests/minute per user.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Import lazily to keep API startup lightweight when prediction endpoints
    # are not being used (e.g., auth/sign-up flows).
    from app.services.prediction_service import prediction_service

    from app.config import settings
    image_bytes = await file.read()
    if len(image_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    prediction = await prediction_service.analyze_image(
        db=db,
        user_id=current_user.id,
        image_bytes=image_bytes,
        original_filename=file.filename or "upload.jpg",
        content_type=file.content_type,
        pet_id=pet_id,
    )

    image_url = prediction.__dict__.get("_image_url")

    return PredictionPublic(
        id=prediction.id,
        user_id=prediction.user_id,
        pet_id=prediction.pet_id,
        top_breed=prediction.top_breed,
        top_confidence=prediction.top_confidence,
        all_predictions=[
            BreedPrediction(
                breed=p["breed"],
                confidence=p["confidence"],
                display_name=p.get("display_name", p["breed"]),
            )
            for p in prediction.all_predictions
        ],
        model_version=prediction.model_version,
        inference_time_ms=prediction.inference_time_ms,
        image_url=image_url,
        created_at=prediction.created_at,
    )


@router.get("", response_model=PaginatedResponse)
async def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    # Import lazily to avoid loading prediction dependencies at app startup.
    from app.services.prediction_service import prediction_service

    predictions, total = await prediction_service.list_by_user(db, current_user.id, page, page_size)
    items = [
        PredictionPublic(
            id=p.id,
            user_id=p.user_id,
            pet_id=p.pet_id,
            top_breed=p.top_breed,
            top_confidence=p.top_confidence,
            all_predictions=[
                BreedPrediction(
                    breed=pred["breed"],
                    confidence=pred["confidence"],
                    display_name=pred.get("display_name", pred["breed"]),
                )
                for pred in p.all_predictions
            ],
            model_version=p.model_version,
            inference_time_ms=p.inference_time_ms,
            created_at=p.created_at,
        )
        for p in predictions
    ]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
