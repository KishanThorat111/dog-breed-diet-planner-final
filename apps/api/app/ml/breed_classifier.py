"""
EfficientNet-B4 breed classifier.
Loads model once at startup, thread-safe inference via torch.no_grad().
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import torch
import torch.nn.functional as F

from app.ml.breed_labels import INDEX_TO_BREED, NUM_CLASSES, BreedInfo
from app.ml.preprocessor import preprocess_image

logger = logging.getLogger(__name__)

MODEL_VERSION = "efficientnet_b4_v1.0"


@dataclass
class BreedPredictionResult:
    breed_key: str
    display_name: str
    confidence: float
    size: str


class BreedClassifier:
    """
    Singleton-style classifier. Instantiate once via ModelLoader, reuse across requests.
    """

    def __init__(self, model_path: str | None = None, device: str = "cpu") -> None:
        self.device = torch.device(device)
        self.model_path = model_path
        self._model: torch.nn.Module | None = None
        self._loaded = False

    def load(self) -> None:
        """Load model weights. Called once at application startup."""
        try:
            import timm
        except ImportError as e:
            raise RuntimeError(
                "timm is required for ML inference. Run: pip install timm"
            ) from e

        logger.info("Loading EfficientNet-B4 model (device=%s)…", self.device)
        model = timm.create_model(
            "efficientnet_b4",
            pretrained=self.model_path is None,  # Use ImageNet pretrained if no custom weights
            num_classes=NUM_CLASSES,
        )

        if self.model_path and os.path.exists(self.model_path):
            logger.info("Loading fine-tuned weights from: %s", self.model_path)
            state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
            model.load_state_dict(state_dict)
        elif self.model_path:
            logger.warning(
                "Model path '%s' not found. Using ImageNet pretrained weights (breeds inaccurate).",
                self.model_path,
            )

        model.eval()
        model.to(self.device)
        self._model = model
        self._loaded = True
        logger.info("Model loaded successfully.")

    def predict(self, image_bytes: bytes, top_k: int = 5) -> tuple[list[BreedPredictionResult], int]:
        """
        Run inference on raw image bytes.
        Returns (predictions sorted by confidence desc, inference_time_ms).
        """
        if not self._loaded or self._model is None:
            raise RuntimeError("Model not loaded. Call .load() first.")

        tensor = preprocess_image(image_bytes)
        tensor = tensor.to(self.device)

        t_start = time.perf_counter()
        with torch.no_grad():
            logits = self._model(tensor)
            probs = F.softmax(logits, dim=1)
        inference_ms = int((time.perf_counter() - t_start) * 1000)

        top_probs, top_indices = torch.topk(probs, k=min(top_k, NUM_CLASSES), dim=1)
        top_probs = top_probs[0].cpu().tolist()
        top_indices = top_indices[0].cpu().tolist()

        results: list[BreedPredictionResult] = []
        for idx, prob in zip(top_indices, top_probs):
            breed_info: BreedInfo = INDEX_TO_BREED[idx]
            results.append(
                BreedPredictionResult(
                    breed_key=breed_info.key,
                    display_name=breed_info.display_name,
                    confidence=round(prob, 4),
                    size=breed_info.size,
                )
            )

        return results, inference_ms

    @property
    def version(self) -> str:
        return MODEL_VERSION
