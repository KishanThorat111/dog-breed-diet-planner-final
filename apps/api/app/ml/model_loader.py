"""
Model loader — singleton that holds the classifier instance.
Loaded once at FastAPI startup via lifespan.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.ml.breed_classifier import BreedClassifier

logger = logging.getLogger(__name__)

_classifier: BreedClassifier | None = None
_load_status: str = "unloaded"  # "unloaded" | "loaded" | "failed"


def get_classifier_status() -> str:
    return _load_status


def get_classifier() -> BreedClassifier:
    """FastAPI dependency / direct accessor for the loaded classifier."""
    if _classifier is None or _load_status != "loaded":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model is not available. Please try again shortly.",
        )
    return _classifier


def initialize_model() -> BreedClassifier:
    """
    Called once at application startup (in lifespan).
    Creates and loads the EfficientNet-B4 classifier.
    Raises on fatal failures; degraded state on weight-load failures.
    """
    global _classifier, _load_status

    device = "cpu"
    classifier = BreedClassifier(
        model_path=settings.ml_model_path or None,
        device=device,
    )
    try:
        classifier.load()
        _load_status = "loaded"
    except Exception as e:
        _load_status = "failed"
        logger.error("Failed to load ML model: %s", e)
        # Don't crash the app — return unloaded classifier
        # get_classifier() will return 503 for inference requests

    _classifier = classifier
    return _classifier
