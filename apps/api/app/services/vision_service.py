"""
AI Vision Breed Classification Service.

Uses Gemini Vision (gemini-1.5-flash) to identify dog breeds from images
with high accuracy. The model is NOT restricted to a fixed list — it is
free to name any breed it sees, and we map the result to our taxonomy
with fuzzy matching.

Falls back to the local EfficientNet ML model when no API key is configured.
"""
from __future__ import annotations

import json
import logging
import re
from difflib import get_close_matches
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Gemini prompt — India-aware, unrestricted breed identification
# ─────────────────────────────────────────────────────────────────────────────
_CLASSIFY_PROMPT = """\
You are an expert canine veterinarian and dog breed identification specialist \
with deep knowledge of dog breeds found in India and worldwide.

TASK: Examine the provided image carefully and identify the dog breed.

IMPORTANT CONTEXT:
- This app is primarily used in India. Pay special attention to:
  * Common breeds in India: Labrador Retriever, German Shepherd, Golden Retriever,
    Pomeranian, Siberian Husky, Beagle, Pug, Rottweiler, Doberman, Great Dane,
    Boxer, Dachshund, Shih Tzu, Cocker Spaniel, Dalmatian, Indian Spitz
  * Indian native breeds: Indian Pariah Dog (Indie/Desi dog), Rajapalayam,
    Mudhol Hound (Caravan Hound), Chippiparai, Kombai, Kanni, Bakharwal Dog,
    Gaddi Kutta, Rampur Hound, Jonangi, Pandikona
  * Mixed breeds and Indies are extremely common — identify confidently as
    "Indian Pariah Dog" or "Mixed Breed" when appropriate.
- Also recognize all international breeds including new/trending ones.

OUTPUT FORMAT: Respond with ONLY a valid JSON object. No markdown, no explanation:
{
  "is_dog": true,
  "top_breed_key": "labrador_retriever",
  "top_display_name": "Labrador Retriever",
  "top_confidence": 0.97,
  "predictions": [
    {"breed_key": "labrador_retriever", "display_name": "Labrador Retriever", "confidence": 0.97},
    {"breed_key": "golden_retriever", "display_name": "Golden Retriever", "confidence": 0.02},
    {"breed_key": "chesapeake_bay_retriever", "display_name": "Chesapeake Bay Retriever", "confidence": 0.01}
  ]
}

RULES:
- Use snake_case for breed_key (e.g. "indian_pariah", "labrador_retriever", "german_shepherd")
- "is_dog" must be false only if there is clearly no dog in the image
- Provide 3-5 predictions sorted by confidence descending
- confidence values must sum to ≤ 1.0
- Be specific: distinguish Labrador from Golden Retriever, Indie from street dog mix, etc.
- If unsure between 2 breeds, still commit to a top prediction with lower confidence
- For Indian Pariah / street dog / desi dog → use breed_key "indian_pariah"
- For Indian Spitz → use breed_key "spitz"
- Temperature is set to near-zero — be deterministic and precise

Use ONLY your visual analysis. Do NOT guess based on context clues outside the dog itself.\
"""


def _parse_response(text: str) -> dict[str, Any] | None:
    """Extract and parse the JSON from Gemini's response text."""
    try:
        cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        # Try to extract JSON object from mixed text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass
        logger.warning("Failed to parse Gemini vision response: %r", text[:300])
        return None


def _map_to_known_breed(breed_key: str, display_name: str = "") -> "BreedInfo | None":
    """
    Map a Gemini-returned breed_key to a known BreedInfo.
    Falls back to fuzzy match on display_name, then creates a dynamic entry.
    """
    from app.ml.breed_labels import KEY_TO_BREED, BREED_LIST, BreedInfo

    # Direct match
    if breed_key in KEY_TO_BREED:
        return KEY_TO_BREED[breed_key]

    # Normalise key and try again
    normalised = re.sub(r"[^a-z0-9]+", "_", breed_key.lower()).strip("_")
    if normalised in KEY_TO_BREED:
        return KEY_TO_BREED[normalised]

    # Fuzzy match against all known keys
    all_keys = list(KEY_TO_BREED.keys())
    matches = get_close_matches(normalised, all_keys, n=1, cutoff=0.55)
    if matches:
        logger.info("Fuzzy-matched '%s' → '%s'", breed_key, matches[0])
        return KEY_TO_BREED[matches[0]]

    # If display_name was provided, try fuzzy match on display names
    if display_name:
        display_lower = display_name.lower()
        for b in BREED_LIST:
            if display_lower in b.display_name.lower() or b.display_name.lower() in display_lower:
                logger.info("Display-name matched '%s' → '%s'", display_name, b.key)
                return b

    # Last resort: create a dynamic entry so we never lose the result
    logger.warning("Unknown breed '%s' ('%s') — creating dynamic entry", breed_key, display_name)
    return BreedInfo(
        index=-1,
        key=normalised or "mixed_breed",
        display_name=display_name or breed_key.replace("_", " ").title(),
        size="medium",
    )


def _jpeg_encode(image_bytes: bytes) -> bytes:
    """
    Re-encode any image to JPEG. Gemini works most reliably with JPEG.
    Returns original bytes if re-encoding fails.
    """
    try:
        import io
        from PIL import Image as _PilImg
        img = _PilImg.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P", "LA"):
            bg = _PilImg.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA"):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return buf.getvalue()
    except Exception:
        return image_bytes


async def classify_breed_with_gemini(
    image_bytes: bytes,
    content_type: str,
) -> dict[str, Any] | None:
    """
    Send image to Gemini Vision and return structured breed classification.
    Returns None if Gemini is not configured or the call fails (caller falls
    back to local EfficientNet model).
    """
    import traceback
    from app.config import settings

    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY is empty — Gemini Vision disabled. "
                       "Set GEMINI_API_KEY in Railway Variables to enable accurate breed detection.")
        return None

    # Pre-process image to JPEG — Gemini handles JPEG most reliably across SDK versions
    jpeg_bytes = _jpeg_encode(image_bytes)
    logger.info("Gemini Vision: sending %d KB JPEG image", len(jpeg_bytes) // 1024)

    raw_text: str = ""

    # ── Attempt 1: google-generativeai SDK (GenerativeModel style) ────────
    try:
        import google.generativeai as genai  # type: ignore[import]
        genai.configure(api_key=settings.gemini_api_key)

        model = genai.GenerativeModel("gemini-1.5-flash")

        # NOTE: Do NOT pass response_mime_type here — it breaks in many SDK
        # versions when combined with image content. We parse JSON ourselves.
        generation_config = genai.types.GenerationConfig(
            temperature=0.02,
            max_output_tokens=600,
        )

        image_part = {"mime_type": "image/jpeg", "data": jpeg_bytes}
        response = model.generate_content(
            contents=[_CLASSIFY_PROMPT, image_part],
            generation_config=generation_config,
        )
        raw_text = response.text or ""
        logger.info("Gemini Vision raw response (%d chars): %s", len(raw_text), raw_text[:200])

    except Exception as exc:
        logger.error(
            "Gemini vision call failed (attempt 1): %s\n%s",
            exc, traceback.format_exc()
        )
        return None

    data = _parse_response(raw_text)
    if not data:
        return None

    if not data.get("is_dog", True):
        logger.info("Gemini: image does not appear to contain a dog.")
        return None

    top_key = data.get("top_breed_key", "")
    top_display = data.get("top_display_name", "")
    top_confidence = float(data.get("top_confidence", 0.0))

    # Build predictions list
    predictions: list[dict[str, Any]] = []
    for p in data.get("predictions", []):
        key = p.get("breed_key", "")
        disp = p.get("display_name", "")
        info = _map_to_known_breed(key, disp)
        if info:
            predictions.append({
                "breed": info.key,
                "display_name": info.display_name,
                "confidence": float(p.get("confidence", 0.0)),
                "size": info.size,
            })

    # Ensure top prediction is in list
    top_info = _map_to_known_breed(top_key, top_display)
    if not top_info:
        top_info = _map_to_known_breed("mixed_breed")

    if not predictions and top_info:
        predictions = [{
            "breed": top_info.key,
            "display_name": top_info.display_name,
            "confidence": top_confidence,
            "size": top_info.size,
        }]

    logger.info(
        "Gemini Vision: top=%s confidence=%.2f alternatives=%d",
        top_info.key if top_info else "unknown",
        top_confidence,
        len(predictions) - 1,
    )

    return {
        "top_breed": top_info.key if top_info else "mixed_breed",
        "top_display_name": top_info.display_name if top_info else "Mixed Breed",
        "top_confidence": top_confidence,
        "all_predictions": predictions,
        "provider": "gemini-vision",
    }

