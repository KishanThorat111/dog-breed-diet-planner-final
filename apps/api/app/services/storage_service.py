"""
Cloudflare R2 storage service (S3-compatible).
Handles: upload, signed URL generation, delete.
"""
from __future__ import annotations

import logging
import threading
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.utils.validators import safe_image_extension

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._client = None
        self._lock = threading.Lock()  # Thread-safe lazy init

    def _get_client(self):  # type: ignore[no-untyped-def]
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
        Upload image bytes to R2. Returns the R2 object key.
        Key format: uploads/{user_id}/{uuid}.{ext}
        Extension is whitelisted — never derived directly from user input.
        """
        ext = safe_image_extension(original_filename)
        # user_id is a UUID string from our DB — safe to include in path
        key = f"uploads/{user_id}/{uuid.uuid4()}.{ext}"

        if settings.is_development and not settings.cloudflare_r2_endpoint_url:
            # Dev fallback: skip upload, return fake key
            logger.warning("R2 not configured. Skipping upload, returning mock key: %s", key)
            return key

        self._get_client().put_object(
            Bucket=settings.cloudflare_r2_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            Metadata={"original-filename": original_filename[:255]},
        )
        logger.info("Uploaded %s bytes to R2: %s", len(file_bytes), key)
        return key

    def get_presigned_url(self, r2_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for direct access (valid for expires_in seconds)."""
        if settings.cloudflare_r2_public_url:
            # If bucket is public, construct URL directly (no signing overhead)
            return f"{settings.cloudflare_r2_public_url.rstrip('/')}/{r2_key}"

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
