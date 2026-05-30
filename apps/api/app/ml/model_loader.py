"""
Model loader — singleton that holds the classifier instance.
Loaded once at FastAPI startup via lifespan.
"""
from __future__ import annotations

import logging
from threading import Lock
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.ml.breed_classifier import BreedClassifier

logger = logging.getLogger(__name__)

_classifier: "BreedClassifier | None" = None
_load_status: str = "unloaded"  # "unloaded" | "loaded" | "failed"
_load_lock = Lock()


def get_classifier_status() -> str:
    return _load_status


def get_classifier() -> "BreedClassifier":
    """FastAPI dependency / direct accessor for the loaded classifier."""
    global _classifier, _load_status

    # Fast path once model is loaded.
    if _classifier is not None and _load_status == "loaded":
        return _classifier

    # Slow path: lazy, one-at-a-time model initialization on first inference.
    with _load_lock:
        if _classifier is not None and _load_status == "loaded":
            return _classifier

        if _classifier is None:
            from app.ml.breed_classifier import BreedClassifier
            _classifier = BreedClassifier(
                model_path=getattr(settings, "ml_model_path", "") or None,
                device="cpu",
            )

        try:
            _classifier.load()
            _load_status = "loaded"
            logger.info("ML model ready (lazy load).")
            return _classifier
        except Exception as e:
            _load_status = "failed"
            logger.error("Failed to load ML model: %s", e)
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI model is not available. Please try again shortly.",
            )


def initialize_model() -> "BreedClassifier":
    """
    Called once at application startup (in lifespan).
    Creates and loads the EfficientNet-B4 classifier.
    Raises on fatal failures; degraded state on weight-load failures.
    """
    # Retained for compatibility with older startup flows.
    # Current runtime uses lazy loading via get_classifier().
    return get_classifier()
