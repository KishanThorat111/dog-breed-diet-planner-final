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
    Uses the Gemini REST v1 API directly (no SDK — avoids gRPC v1beta routing
    issues in google-generativeai 0.8.x).
    Returns None if Gemini is not configured or the call fails.
    """
    import base64
    import io as _io
    import json as _json
    import traceback
    import urllib.error
    import urllib.request
    from app.config import settings

    if not settings.gemini_api_key:
        logger.warning(
            "GEMINI_API_KEY is empty — Gemini Vision disabled. "
            "Set it in Railway Variables for accurate breed detection."
        )
        return None

    # Pre-process image to JPEG
    jpeg_bytes = _jpeg_encode(image_bytes)
    logger.info("Gemini Vision: sending %d KB JPEG", len(jpeg_bytes) // 1024)

    b64_image = base64.b64encode(jpeg_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": _CLASSIFY_PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.02,
            "maxOutputTokens": 600,
        },
    }

    # gemini-2.5-flash is the current recommended model (Tier 1 Postpay)
    # Falls back to gemini-2.0-flash if 2.5 preview is unavailable
    _MODELS = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    import asyncio as _asyncio

    raw_text: str = ""
    last_error: str = ""

    for model_name in _MODELS:
        api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={settings.gemini_api_key}"
        )
        logger.info("Gemini Vision: trying model %s", model_name)
        try:
            req_body = _json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url=api_url,
                data=req_body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            loop = _asyncio.get_running_loop()

            def _http_call() -> str:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read().decode("utf-8")

            resp_text = await loop.run_in_executor(None, _http_call)
            resp_data = _json.loads(resp_text)
            raw_text = (
                resp_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            logger.info("Gemini %s response (%d chars): %s", model_name, len(raw_text), raw_text[:200])
            break  # success — stop trying other models

        except urllib.error.HTTPError as http_err:
            err_body = http_err.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {http_err.code} ({model_name}): {err_body[:300]}"
            logger.warning("Gemini %s failed: %s", model_name, last_error)
            if http_err.code in (429, 404):
                # Rate limited or model unavailable — try next model
                await _asyncio.sleep(1)
                continue
            # Other HTTP error — non-retryable
            logger.error("Gemini REST non-retryable error: %s", last_error)
            return None
        except Exception as exc:
            logger.error("Gemini REST call failed (%s): %s\n%s", model_name, exc, traceback.format_exc())
            return None
    else:
        # All models exhausted (all returned 429)
        logger.error("All Gemini models rate-limited. Last error: %s", last_error)
        return None

    if not raw_text:
        logger.warning("Gemini returned empty response text")
        return None

    data = _parse_response(raw_text)
    if not data:
        return None

    if not data.get("is_dog", True):
        logger.info("Gemini: image does not appear to contain a dog.")
        # Return special sentinel dict so caller knows Gemini explicitly
        # rejected this image — do NOT fall back to EfficientNet.
        return {"no_dog_detected": True}

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

