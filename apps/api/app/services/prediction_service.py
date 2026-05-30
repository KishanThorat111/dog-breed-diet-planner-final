from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.prediction import AIPrediction
from app.models.upload import Upload
from app.ml.pipeline import InferencePipelineResult
from app.services.storage_service import storage_service
from app.utils.cache import cache
from app.utils.validators import validate_image_bytes

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour


class PredictionService:
    async def analyze_image(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        image_bytes: bytes,
        original_filename: str,
        content_type: str,
        pet_id: uuid.UUID | None = None,
    ) -> AIPrediction:
        # 1. Validate image (magic-byte MIME check, PIL open, dimension check)
        validate_image_bytes(image_bytes, content_type)

        # 2. Hash for cache key and deduplication
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        # 3. Check in-process cache — return DB record directly if already analysed
        cached_result: dict[str, Any] | None = await self._get_cached_result(image_hash)
        if cached_result is not None:
            logger.info("Cache hit for image hash %s", image_hash[:12])
            # Still need a fresh DB record linked to this user/pet, but we
            # can skip inference and R2 upload of an identical image.
            return await self._create_prediction_from_cache(
                db, user_id, pet_id, image_hash, cached_result, original_filename, content_type, image_bytes
            )

        loop = asyncio.get_running_loop()

        # 4. Gemini Vision only (no local model fallback on e2-micro).
        from app.services.vision_service import classify_breed_with_gemini
        from fastapi import HTTPException

        ai_vision = await classify_breed_with_gemini(image_bytes, content_type)

        if ai_vision is not None and ai_vision.get("no_dog_detected"):
            raise HTTPException(
                status_code=422,
                detail="No dog detected in this image. Please upload a clear photo of a dog.",
            )

        if ai_vision is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini AI service is unavailable. "
                    "Please retry in a few moments."
                ),
            )

        # Build a normalized InferencePipelineResult from Gemini's response
        result = InferencePipelineResult(
            top_breed=ai_vision["top_breed"],
            top_confidence=ai_vision["top_confidence"],
            top_display_name=ai_vision["top_display_name"],
            all_predictions=ai_vision["all_predictions"],
            model_version=f"{ai_vision.get('provider', 'gemini')}",
            inference_time_ms=0,
            image_hash=image_hash,
        )
        logger.info(
            "Gemini Vision classified breed=%s confidence=%.2f",
            result.top_breed,
            result.top_confidence,
        )

        # 5. Upload to R2 — non-fatal if R2 is not configured
        r2_key: str | None = None
        try:
            r2_key = await loop.run_in_executor(
                None,
                lambda: storage_service.upload_image(
                    image_bytes, str(user_id), original_filename, content_type
                ),
            )
        except Exception as r2_err:
            logger.warning("R2 upload skipped (non-fatal): %s", r2_err)

        # 6. Persist upload record (only if R2 upload succeeded)
        upload_id: uuid.UUID | None = None
        if r2_key:
            upload = Upload(
                user_id=user_id,
                r2_key=r2_key,
                r2_bucket=settings.cloudflare_r2_bucket_name,
                original_filename=original_filename[:255],
                content_type=content_type,
                size_bytes=len(image_bytes),
                sha256_hash=image_hash,
            )
            db.add(upload)
            await db.flush()  # Get upload.id without committing
            upload_id = upload.id

        # 7. Persist prediction
        prediction = AIPrediction(
            user_id=user_id,
            pet_id=pet_id,
            upload_id=upload_id,
            top_breed=result.top_breed,
            top_confidence=result.top_confidence,
            all_predictions=result.all_predictions,
            model_version=result.model_version,
            inference_time_ms=result.inference_time_ms,
        )
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)

        # 8. Cache the result for future identical uploads
        await self._cache_result(image_hash, result)

        # 9. Attach image URL for response (None if R2 not configured)
        image_url = storage_service.get_presigned_url(r2_key) if r2_key else None
        prediction.__dict__["_image_url"] = image_url

        logger.info(
            "Prediction id=%s breed=%s confidence=%.2f inference=%dms",
            prediction.id, result.top_breed, result.top_confidence, result.inference_time_ms,
        )
        return prediction

    async def _get_cached_result(self, image_hash: str) -> dict[str, Any] | None:
        """Return cached inference result dict or None (best-effort)."""
        try:
            return await cache.get(f"prediction:{image_hash}")
        except Exception:
            return None

    async def _cache_result(self, image_hash: str, result: InferencePipelineResult) -> None:
        """Persist inference result to in-process cache (best-effort)."""
        try:
            await cache.set(
                f"prediction:{image_hash}",
                {
                    "top_breed": result.top_breed,
                    "top_confidence": result.top_confidence,
                    "top_display_name": result.top_display_name,
                    "all_predictions": result.all_predictions,
                    "model_version": result.model_version,
                    "inference_time_ms": result.inference_time_ms,
                },
                ttl_seconds=_CACHE_TTL,
            )
        except Exception as e:
            logger.debug("Cache set failed: %s", e)

    async def _create_prediction_from_cache(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        pet_id: uuid.UUID | None,
        image_hash: str,
        cached: dict[str, Any],
        original_filename: str,
        content_type: str,
        image_bytes: bytes,
    ) -> AIPrediction:
        """Create a new DB prediction record using cached inference data (no R2 upload, no re-inference)."""
        loop = asyncio.get_running_loop()
        r2_key: str | None = None
        upload_id: uuid.UUID | None = None
        try:
            r2_key = await loop.run_in_executor(
                None,
                lambda: storage_service.upload_image(
                    image_bytes, str(user_id), original_filename, content_type
                ),
            )
            upload = Upload(
                user_id=user_id,
                r2_key=r2_key,
                r2_bucket=settings.cloudflare_r2_bucket_name,
                original_filename=original_filename[:255],
                content_type=content_type,
                size_bytes=len(image_bytes),
                sha256_hash=image_hash,
            )
            db.add(upload)
            await db.flush()
            upload_id = upload.id
        except Exception as r2_err:
            logger.warning("R2 upload skipped (non-fatal): %s", r2_err)

        prediction = AIPrediction(
            user_id=user_id,
            pet_id=pet_id,
            upload_id=upload_id,
            top_breed=cached["top_breed"],
            top_confidence=cached["top_confidence"],
            all_predictions=cached["all_predictions"],
            model_version=cached["model_version"],
            inference_time_ms=cached.get("inference_time_ms", 0),
        )
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)
        prediction.__dict__["_image_url"] = (
            storage_service.get_presigned_url(r2_key) if r2_key else None
        )
        prediction.__dict__["_cached"] = True
        return prediction

    async def list_by_user(
        self, db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[AIPrediction], int]:
        from sqlalchemy import func
        base = select(AIPrediction).where(AIPrediction.user_id == user_id)
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()
        result = await db.execute(
            base.order_by(AIPrediction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), total  # type: ignore[return-value]


prediction_service = PredictionService()
