from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from app.ml.pipeline import InferencePipelineResult
from app.models.user import User
from app.services.prediction_service import prediction_service
from app.services.vision_service import GeminiErrorType, GeminiVisionError

def _valid_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_prediction_service_uses_local_fallback_when_gemini_response_is_invalid(db_session) -> None:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            email=f"fallback-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="x",
            full_name="Fallback User",
            is_active=True,
        )
    )
    await db_session.commit()

    fallback_result = InferencePipelineResult(
        top_breed="thai_ridgeback",
        top_confidence=0.74,
        top_display_name="Thai Ridgeback",
        all_predictions=[
            {
                "breed": "thai_ridgeback",
                "display_name": "Thai Ridgeback",
                "confidence": 0.74,
                "size": "medium",
            },
            {
                "breed": "pharaoh_hound",
                "display_name": "Pharaoh Hound",
                "confidence": 0.26,
                "size": "medium",
            },
        ],
        model_version="efficientnet_b4_v1.0",
        inference_time_ms=42,
        image_hash="abc123",
    )

    with (
        patch(
            "app.services.vision_service.classify_breed_with_gemini",
            new_callable=AsyncMock,
            side_effect=GeminiVisionError(
                GeminiErrorType.INVALID_RESPONSE,
                "malformed JSON from Gemini",
            ),
        ),
        patch("app.ml.pipeline.run_inference", return_value=fallback_result),
        patch("app.services.prediction_service.storage_service.upload_image", side_effect=RuntimeError("r2 not configured")),
    ):
        prediction = await prediction_service.analyze_image(
            db=db_session,
            user_id=user_id,
            image_bytes=_valid_jpeg_bytes(),
            original_filename="rare-breed.jpg",
            content_type="image/jpeg",
            pet_id=None,
        )

    assert prediction.top_breed == "thai_ridgeback"
    assert float(prediction.top_confidence) == pytest.approx(0.74, abs=1e-3)
    assert prediction.model_version == "efficientnet_b4_v1.0"
    assert prediction.inference_time_ms == 42
    assert prediction.upload_id is None
