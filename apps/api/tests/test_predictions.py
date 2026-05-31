"""Tests for prediction endpoints with service layer mocked."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# Minimal valid JPEG bytes
_TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_returns_prediction(self, client: AsyncClient) -> None:
        fake_prediction = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            pet_id=None,
            top_breed="golden_retriever",
            top_confidence=0.95,
            all_predictions=[
                {
                    "breed": "golden_retriever",
                    "display_name": "Golden Retriever",
                    "confidence": 0.95,
                }
            ],
            model_version="gemini-vision",
            inference_time_ms=120,
            created_at=datetime.now(timezone.utc),
            _image_url="https://r2.example.com/uploads/test/abc.jpg",
        )

        with patch(
            "app.services.prediction_service.prediction_service.analyze_image",
            new_callable=AsyncMock,
            return_value=fake_prediction,
        ):
            response = await client.post(
                "/api/v1/predictions/analyze",
                files={"file": ("test.jpg", io.BytesIO(_TINY_JPEG), "image/jpeg")},
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["top_breed"] == "golden_retriever"
        assert float(body["top_confidence"]) >= 0.9
        assert body["image_url"] is not None

    @pytest.mark.asyncio
    async def test_analyze_rejects_unsupported_file_type(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/predictions/analyze",
            files={"file": ("exploit.txt", io.BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 415


class TestPredictionsListEndpoint:
    @pytest.mark.asyncio
    async def test_list_predictions_returns_paginated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/predictions")
        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
