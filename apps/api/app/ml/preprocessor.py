"""
Image preprocessor for EfficientNet-B4 inference.
Input: raw image bytes (JPEG/PNG/WEBP)
Output: normalized torch.Tensor ready for model input
"""
from __future__ import annotations

import io
import logging

import numpy as np
import torch
import torchvision.transforms.v2 as T
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# EfficientNet-B4 input spec
INPUT_SIZE = 380
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_transform = T.Compose([
    T.Resize((INPUT_SIZE, INPUT_SIZE), interpolation=T.InterpolationMode.BICUBIC, antialias=True),
    T.ToImage(),
    T.ToDtype(torch.float32, scale=True),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])


def preprocess_image(image_bytes: bytes) -> torch.Tensor:
    """
    Decode image bytes → validate → transform → return (1, 3, 380, 380) tensor.
    Raises ValueError for corrupt/non-image data.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Auto-correct EXIF orientation (important for mobile camera uploads)
        img = ImageOps.exif_transpose(img)
        # Ensure RGB (handles RGBA, grayscale, etc.)
        img = img.convert("RGB")
    except Exception as e:
        raise ValueError(f"Cannot decode image: {e}") from e

    tensor: torch.Tensor = _transform(img)
    return tensor.unsqueeze(0)  # Add batch dimension → (1, 3, 380, 380)
