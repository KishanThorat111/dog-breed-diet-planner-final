"""
Cloudflare R2 storage service (S3-compatible).
Handles: upload, signed URL generation, delete.
Images are compressed with Pillow before upload (JPEG 85%, max 1920px)
to reduce storage costs without perceptible quality loss.
"""
from __future__ import annotations

import io
import logging
import threading
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings
from app.utils.validators import safe_image_extension

logger = logging.getLogger(__name__)

# Compression settings — JPEG 85 is transparent quality for photographs
_MAX_DIMENSION = 1920      # px — enough for web/mobile display
_JPEG_QUALITY = 85         # 85 gives ~70-80% size reduction from raw DSLR images
_COMPRESS_THRESHOLD = 100 * 1024  # Only compress files > 100 KB


def compress_image_bytes(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """
    Compress image_bytes using Pillow.
    Returns (compressed_bytes, new_content_type).
    Falls back to original bytes if anything goes wrong.
    """
    if len(image_bytes) < _COMPRESS_THRESHOLD:
        return image_bytes, content_type

    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert palette/RGBA to RGB for JPEG compatibility
        if img.mode in ("P", "RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA"):
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if image is larger than max dimension (preserves aspect ratio)
        w, h = img.size
        if w > _MAX_DIMENSION or h > _MAX_DIMENSION:
            ratio = min(_MAX_DIMENSION / w, _MAX_DIMENSION / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        compressed = buf.getvalue()

        # Only use compressed version if it's smaller
        if len(compressed) < len(image_bytes):
            saved_pct = round((1 - len(compressed) / len(image_bytes)) * 100)
            logger.info(
                "Image compressed: %d KB → %d KB (-%d%%)",
                len(image_bytes) // 1024,
                len(compressed) // 1024,
                saved_pct,
            )
            return compressed, "image/jpeg"

    except Exception as exc:
        logger.warning("Image compression failed (using original): %s", exc)

    return image_bytes, content_type


class StorageService:
    def __init__(self) -> None:
        self._client = None
        self._lock = threading.Lock()  # Thread-safe lazy init

    def _is_configured(self) -> bool:
        return all(
            [
                settings.cloudflare_r2_endpoint_url,
                settings.cloudflare_r2_access_key_id,
                settings.cloudflare_r2_secret_access_key,
                settings.cloudflare_r2_bucket_name,
            ]
        )

    def _get_client(self):  # type: ignore[no-untyped-def]
        if not self._is_configured():
            raise RuntimeError("Cloudflare R2 is not configured")
        if self._client is None:
            with self._lock:
                if self._client is None:  # Double-checked locking
                    self._client = boto3.client(
                        "s3",
                        endpoint_url=settings.cloudflare_r2_endpoint_url,
                        aws_access_key_id=settings.cloudflare_r2_access_key_id,
                        aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
                        config=Config(
                            region_name="auto",
                            retries={"max_attempts": 3, "mode": "adaptive"},
                        ),
                    )
        return self._client

    def upload_image(
        self,
        file_bytes: bytes,
        user_id: str,
        original_filename: str,
        content_type: str,
    ) -> str:
        """
        Compress then upload image bytes to R2. Returns the R2 object key.
        Key format: uploads/{user_id}/{uuid}.jpg (always JPEG after compression)
        """
        # Compress server-side before storing
        file_bytes, content_type = compress_image_bytes(file_bytes, content_type)

        # Use .jpg extension after compression (we always output JPEG)
        ext = "jpg" if content_type == "image/jpeg" else safe_image_extension(original_filename)
        key = f"uploads/{user_id}/{uuid.uuid4()}.{ext}"

        if not self._is_configured():
            raise RuntimeError("Cloudflare R2 is not configured")

        self._get_client().put_object(
            Bucket=settings.cloudflare_r2_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={"original-filename": original_filename[:255]},
        )
        logger.info("Uploaded %s KB to R2: %s", len(file_bytes) // 1024, key)
        return key

    def get_presigned_url(self, r2_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for direct access (valid for expires_in seconds)."""
        if settings.cloudflare_r2_public_url:
            # If bucket is public, construct URL directly (no signing overhead)
            return f"{settings.cloudflare_r2_public_url.rstrip('/')}/{r2_key}"

        if not self._is_configured():
            raise RuntimeError("Cloudflare R2 is not configured")

        return self._get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.cloudflare_r2_bucket_name, "Key": r2_key},
            ExpiresIn=expires_in,
        )

    def delete_object(self, r2_key: str) -> None:
        """Delete object from R2."""
        try:
            self._get_client().delete_object(
                Bucket=settings.cloudflare_r2_bucket_name,
                Key=r2_key,
            )
        except ClientError as e:
            logger.error("Failed to delete R2 object %s: %s", r2_key, e)


storage_service = StorageService()
