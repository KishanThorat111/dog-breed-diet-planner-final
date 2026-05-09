"""
Image validation using python-magic for MIME type verification.
Server-side validation — never trust Content-Type header alone.
"""
from __future__ import annotations

import io
import logging

from fastapi import HTTPException, status
from PIL import Image, ImageFile

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_DIMENSION = 4096  # pixels — defence against decompression bombs

# PIL decompression-bomb guard: refuse images with more than ~50 MP
Image.MAX_IMAGE_PIXELS = 50_000_000
ImageFile.LOAD_TRUNCATED_IMAGES = False  # Reject truncated uploads


def validate_image_bytes(image_bytes: bytes, declared_content_type: str) -> None:
    """
    Validate image bytes:
    1. Verify MIME type using file magic bytes (not just Content-Type header)
    2. Confirm PIL can open it (guards against corrupt / polyglot files)
    3. Check for oversized dimensions
    Raises HTTPException on validation failure.
    """
    # 1. Magic-byte MIME verification
    try:
        import magic as libmagic
        detected_mime = libmagic.from_buffer(image_bytes, mime=True)
    except ImportError:
        logger.warning("python-magic not available — falling back to header MIME check")
        detected_mime = declared_content_type

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid image format detected: {detected_mime}. Allowed: JPEG, PNG, WEBP",
        )

    # 2. PIL open + dimension check
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # Catches truncated/corrupt files; moves file pointer to end
        # Reopen for size check — verify() leaves handle exhausted
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image dimensions too large: {w}�—{h}. Maximum: {MAX_IMAGE_DIMENSION}px",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupt image data.",
        )


def safe_image_extension(filename: str) -> str:
    """Return a sanitised, whitelisted extension from a user-supplied filename."""
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ALLOWED_EXTENSIONS:
            return "jpg" if ext == "jpeg" else ext
    return "jpg"
