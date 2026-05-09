from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_optional_user, ANONYMOUS_USER_ID
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
    current_user: User | None = Depends(get_optional_user),
) -> PredictionPublic:
    """
    Upload a dog image and receive AI breed identification.
    Auth is optional — anonymous users use the shared ANONYMOUS_USER_ID.
    """
    user_id = current_user.id if current_user else ANONYMOUS_USER_ID
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
        user_id=user_id,
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
    current_user: User | None = Depends(get_optional_user),
) -> PaginatedResponse:
    # Anonymous users have no listing — only return data for authenticated users.
    if current_user is None:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

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


@router.get("/gemini-status")
async def gemini_status() -> dict:
    """
    Quick diagnostic: checks whether Gemini Vision is configured and reachable.
    Calls the Gemini REST v1 API directly (bypasses SDK gRPC/v1beta issues).
    """
    import base64
    import io
    import json as _json
    import traceback
    import urllib.error
    import urllib.request
    from app.config import settings
    from PIL import Image as _Img

    result: dict = {
        "gemini_api_key_set": bool(settings.gemini_api_key),
        "gemini_api_key_prefix": settings.gemini_api_key[:8] + "..." if settings.gemini_api_key else "",
        "api_method": "REST v1beta",
        "call_success": False,
        "model_used": None,
        "error": None,
        "raw_response": None,
    }

    if not settings.gemini_api_key:
        return result

    # Create a tiny 10x10 white JPEG
    buf = io.BytesIO()
    _Img.new("RGB", (10, 10), (255, 255, 255)).save(buf, format="JPEG")
    tiny_jpeg = buf.getvalue()
    b64_img = base64.b64encode(tiny_jpeg).decode("utf-8")

    payload = {
        "contents": [{"parts": [
            {"text": "Is there a dog in this image? Reply yes or no."},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
        ]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 20},
    }

    _MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-8b"]
    last_error = ""

    for model_name in _MODELS:
        api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={settings.gemini_api_key}"
        )
        try:
            req = urllib.request.Request(
                url=api_url,
                data=_json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                resp_data = _json.loads(r.read().decode())
            result["call_success"] = True
            result["model_used"] = model_name
            result["raw_response"] = (
                resp_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )[:200]
            break
        except urllib.error.HTTPError as http_err:
            last_error = f"HTTP {http_err.code} ({model_name}): {http_err.read().decode()[:200]}"
            if http_err.code == 429:
                continue  # try next model
            result["error"] = last_error
            return result
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["traceback"] = traceback.format_exc()
            return result

    if not result["call_success"]:
        result["error"] = f"All models rate-limited. Last: {last_error}"

    return result
