"""
High-level inference pipeline.
Orchestrates: validate → preprocess → classify → format output.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.ml.model_loader import get_classifier

if TYPE_CHECKING:
    from app.ml.breed_classifier import BreedClassifier

logger = logging.getLogger(__name__)


@dataclass
class InferencePipelineResult:
    top_breed: str
    top_confidence: float
    top_display_name: str
    all_predictions: list[dict]
    model_version: str
    inference_time_ms: int
    image_hash: str  # sha256 for caching


def run_inference(image_bytes: bytes) -> InferencePipelineResult:
    """
    Execute the full inference pipeline on raw image bytes.
    This is synchronous and CPU-bound. Call from a thread pool in async contexts.
    """
    classifier: "BreedClassifier" = get_classifier()

    image_hash = hashlib.sha256(image_bytes).hexdigest()
    predictions, inference_ms = classifier.predict(image_bytes, top_k=5)

    if not predictions:
        raise RuntimeError("Model returned empty predictions.")

    top = predictions[0]

    return InferencePipelineResult(
        top_breed=top.breed_key,
        top_confidence=top.confidence,
        top_display_name=top.display_name,
        all_predictions=[
            {
                "breed": p.breed_key,
                "display_name": p.display_name,
                "confidence": p.confidence,
                "size": p.size,
            }
            for p in predictions
        ],
        model_version=classifier.version,
        inference_time_ms=inference_ms,
        image_hash=image_hash,
    )
