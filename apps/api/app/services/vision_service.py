"""
AI Vision Breed Classification Service.

Uses Gemini Vision (gemini-2.5-flash / gemini-2.5-flash-lite) to identify dog breeds from images
with high accuracy. The model is NOT restricted to a fixed list — it is
free to name any breed it sees, and we map the result to our taxonomy
with fuzzy matching.

Production-grade: error handling, retry logic, circuit breaker, structured logging.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import traceback
from difflib import get_close_matches
from enum import Enum
from typing import Any, Optional
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Error Types & Structures (Production-grade error handling)
# ─────────────────────────────────────────────────────────────────────────────

class GeminiErrorType(str, Enum):
    """Categorizes Gemini API failures for proper handling and client response."""
    QUOTA_EXHAUSTED = "quota_exhausted"
    INVALID_KEY = "invalid_key"
    PERMISSION_DENIED = "permission_denied"
    MODEL_UNAVAILABLE = "model_unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    EMPTY_RESPONSE = "empty_response"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class GeminiVisionError(Exception):
    """Structured error type for Gemini Vision API failures."""
    def __init__(
        self,
        error_type: GeminiErrorType,
        message: str,
        http_code: Optional[int] = None,
        details: Optional[dict] = None,
    ):
        self.error_type = error_type
        self.message = message
        self.http_code = http_code
        self.details = details or {}
        super().__init__(message)


class CircuitBreaker:
    """Simple circuit breaker for model failure tracking (prevents hammering failed models)."""
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.last_failure_time = 0.0
        self.is_open = False

    def record_failure(self) -> None:
        """Record a failure and open circuit if threshold exceeded."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker OPEN after {self.failures} failures")

    def record_success(self) -> None:
        """Reset circuit breaker on success."""
        self.failures = 0
        self.is_open = False

    def allow_request(self) -> bool:
        """Check if request is allowed (circuit closed or cooldown expired)."""
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.cooldown_seconds:
            self.is_open = False
            self.failures = 0
            logger.info("Circuit breaker CLOSED (cooldown reset)")
            return True
        return False


# Circuit breakers per model (one per model instance)
_circuit_breakers = {}

def _get_circuit_breaker(model_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for a model."""
    if model_name not in _circuit_breakers:
        from app.config import settings
        _circuit_breakers[model_name] = CircuitBreaker(
            failure_threshold=settings.gemini_circuit_breaker_failure_threshold,
            cooldown_seconds=settings.gemini_circuit_breaker_cooldown_seconds,
        )
    return _circuit_breakers[model_name]

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


def _safe_confidence(value: Any, default: float = 0.0) -> float:
    """Parse confidence values from float/int/string/percent forms."""
    try:
        if isinstance(value, (int, float)):
            parsed = float(value)
        elif isinstance(value, str):
            raw = value.strip()
            is_percent = raw.endswith("%")
            raw = raw.replace("%", "")
            parsed = float(raw)
            if is_percent:
                parsed = parsed / 100.0
        else:
            return default

        if parsed > 1.0:
            parsed = parsed / 100.0
        return max(0.0, min(parsed, 1.0))
    except Exception:
        return default


def _extract_first_json_object(text: str) -> str | None:
    """Return the first balanced JSON object found in text."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for idx in range(start, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return None


def _normalize_response_payload(raw: Any) -> dict[str, Any] | None:
    """Normalize Gemini JSON payload variants into the canonical schema."""
    if not isinstance(raw, dict):
        return None

    is_dog_raw = raw.get("is_dog", True)
    if isinstance(is_dog_raw, str):
        is_dog = is_dog_raw.strip().lower() not in {"false", "no", "0"}
    else:
        is_dog = bool(is_dog_raw)

    top_breed_key = (
        raw.get("top_breed_key")
        or raw.get("top_breed")
        or raw.get("breed_key")
        or raw.get("breed")
        or ""
    )
    top_display_name = (
        raw.get("top_display_name")
        or raw.get("top_breed_name")
        or raw.get("display_name")
        or ""
    )
    top_confidence = _safe_confidence(
        raw.get("top_confidence")
        if raw.get("top_confidence") is not None
        else raw.get("confidence"),
        default=0.0,
    )

    raw_predictions = raw.get("predictions")
    if not isinstance(raw_predictions, list):
        raw_predictions = raw.get("all_predictions") if isinstance(raw.get("all_predictions"), list) else []

    predictions: list[dict[str, Any]] = []
    for item in raw_predictions:
        if not isinstance(item, dict):
            continue
        breed_key = item.get("breed_key") or item.get("breed") or ""
        display_name = item.get("display_name") or item.get("breed_name") or ""
        confidence = _safe_confidence(
            item.get("confidence")
            if item.get("confidence") is not None
            else item.get("score"),
            default=0.0,
        )
        if not breed_key and not display_name:
            continue
        if not breed_key and display_name:
            breed_key = re.sub(r"[^a-z0-9]+", "_", str(display_name).lower()).strip("_")
        if not display_name and breed_key:
            display_name = str(breed_key).replace("_", " ").title()
        predictions.append(
            {
                "breed_key": str(breed_key),
                "display_name": str(display_name),
                "confidence": confidence,
            }
        )

    predictions.sort(key=lambda p: p["confidence"], reverse=True)

    if not top_breed_key and predictions:
        top_breed_key = predictions[0]["breed_key"]
    if not top_display_name and predictions:
        top_display_name = predictions[0]["display_name"]
    if top_confidence <= 0 and predictions:
        top_confidence = predictions[0]["confidence"]

    if not top_breed_key:
        return None

    if not top_display_name:
        top_display_name = str(top_breed_key).replace("_", " ").title()

    if not predictions:
        predictions = [
            {
                "breed_key": str(top_breed_key),
                "display_name": str(top_display_name),
                "confidence": max(top_confidence, 0.01),
            }
        ]

    return {
        "is_dog": is_dog,
        "top_breed_key": str(top_breed_key),
        "top_display_name": str(top_display_name),
        "top_confidence": top_confidence,
        "predictions": predictions,
    }


def _parse_response(text: str) -> dict[str, Any] | None:
    """
    Extract and parse the JSON from Gemini's response text.
    Handles markdown code blocks and mixed text responses.
    Returns dict if successful, None if parsing fails.
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid response text: %s", type(text))
        return None
        
    # First attempt: parse the full cleaned text.
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        parsed = json.loads(cleaned)
        normalized = _normalize_response_payload(parsed)
        if normalized is not None:
            return normalized
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug("Failed to parse cleaned JSON: %s", e)

    # Second attempt: extract first balanced object from mixed text.
    extracted = _extract_first_json_object(cleaned)
    if extracted:
        try:
            parsed = json.loads(extracted)
            normalized = _normalize_response_payload(parsed)
            if normalized is not None:
                logger.debug("Successfully extracted and normalized JSON from mixed text")
                return normalized
        except (json.JSONDecodeError, ValueError) as e2:
            logger.debug("Failed to parse extracted JSON: %s", e2)

    logger.error("Could not parse any valid JSON from response: %r", text[:300])
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
    user_id: "uuid.UUID | None" = None,
    reference_type: str | None = None,
    reference_id: "uuid.UUID | None" = None,
) -> dict[str, Any]:
    """
    Send image to Gemini Vision and return structured breed classification.
    Uses the Gemini REST v1 API directly (no SDK — avoids gRPC v1beta routing issues).
    
    Raises GeminiVisionError on failure with detailed error type and context.
    Implements retry logic with exponential backoff for transient failures.
    Uses circuit breaker to prevent hammering failed models.
    
    Returns:
        dict with keys: top_breed, top_display_name, top_confidence, all_predictions, provider
        
    Raises:
        GeminiVisionError: with error_type indicating failure reason (quota, invalid key, timeout, etc.)
    """
    import base64
    import io as _io
    import json as _json
    from app.config import settings

    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not configured")
        raise GeminiVisionError(
            GeminiErrorType.INVALID_KEY,
            "Gemini API key not configured",
            details={"action": "Set GEMINI_API_KEY environment variable"},
        )

    # Pre-process image to JPEG for maximum compatibility
    jpeg_bytes = _jpeg_encode(image_bytes)
    logger.info("Gemini Vision: sending %d KB image", len(jpeg_bytes) // 1024)

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

    # Try models in order with exponential backoff on failures
    # Primary: gemini-2.5-flash (best balance: image understanding + cost)
    # Fallback: gemini-2.5-flash-lite (cost-efficient alternative)
    # NOTE: gemini-2.0-flash was shut down on June 1, 2026
    _MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    
    last_error: Optional[GeminiVisionError] = None

    for model_name in _MODELS:
        # Check circuit breaker
        cb = _get_circuit_breaker(model_name)
        if not cb.allow_request():
            logger.debug(f"Circuit breaker OPEN for {model_name}, skipping")
            continue

        # Retry logic with exponential backoff (1s, 2s, 4s)
        for attempt in range(1, 4):  # 3 attempts
            backoff_seconds = 2 ** (attempt - 1)  # 1, 2, 4
            
            if attempt > 1:
                logger.info(f"Retry {attempt}/3 for {model_name} after {backoff_seconds}s backoff")
                await asyncio.sleep(backoff_seconds)

            try:
                api_url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={settings.gemini_api_key}"
                )
                logger.debug(f"Gemini Vision: calling {model_name} (attempt {attempt}/3)")
                
                req_body = _json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url=api_url,
                    data=req_body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                
                loop = asyncio.get_running_loop()

                def _http_call() -> str:
                    with urllib.request.urlopen(req, timeout=settings.gemini_vision_timeout_seconds) as resp:
                        return resp.read().decode("utf-8")

                resp_text = await loop.run_in_executor(None, _http_call)
                resp_data = _json.loads(resp_text)
                
                raw_text = (
                    resp_data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                
                logger.info(
                    f"Gemini {model_name} SUCCESS: got response ({len(raw_text)} chars)"
                )
                
                if not raw_text:
                    raise GeminiVisionError(
                        GeminiErrorType.EMPTY_RESPONSE,
                        f"{model_name} returned empty response",
                    )

                # Attempt parsing
                data = _parse_response(raw_text)
                if not data:
                    raise GeminiVisionError(
                        GeminiErrorType.INVALID_RESPONSE,
                        f"Failed to parse {model_name} response",
                        details={"response_sample": raw_text[:200]},
                    )

                # Record success and process result
                cb.record_success()
                
                if not data.get("is_dog", True):
                    logger.info("Gemini: image does not contain a dog")
                    raise GeminiVisionError(
                        GeminiErrorType.EMPTY_RESPONSE,
                        "No dog detected in image",
                        details={"no_dog_detected": True},
                    )

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
                    f"Gemini Vision: breed={top_info.key if top_info else 'unknown'} "
                    f"confidence={top_confidence:.2f} model={model_name}"
                )

                # Attempt to record usage information if present in response
                try:
                    from app.services.ai_usage_service import schedule_record
                    # Look for usage metadata in a few possible locations
                    usage_meta = resp_data.get("metadata", {}) or {}
                    cand_meta = resp_data.get("candidates", [{}])[0].get("metadata", {}) or {}
                    usage = usage_meta.get("usage") or usage_meta.get("usage_metadata") or cand_meta.get("usage") or cand_meta.get("usage_metadata") or {}
                    prompt_tokens = int(usage.get("prompt_token_count") or usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                    completion_tokens = int(usage.get("candidates_token_count") or usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                    try:
                        schedule_record(
                            user_id=user_id,
                            provider="gemini-vision",
                            model=model_name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            caller="vision_classify",
                            reference_type=reference_type,
                            reference_id=reference_id,
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

                return {
                    "top_breed": top_info.key if top_info else "mixed_breed",
                    "top_display_name": top_info.display_name if top_info else "Mixed Breed",
                    "top_confidence": top_confidence,
                    "all_predictions": predictions,
                    "provider": "gemini-vision",
                }

            except GeminiVisionError:
                # Re-raise our structured errors
                raise
            
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8", errors="replace")
                error_detail = f"HTTP {http_err.code}: {err_body[:200]}"
                
                logger.warning(f"Gemini {model_name} HTTP error (attempt {attempt}/3): {error_detail}")

                # Determine error type from HTTP code
                if http_err.code == 401:
                    raise GeminiVisionError(
                        GeminiErrorType.INVALID_KEY,
                        "Invalid or expired Gemini API key",
                        http_code=401,
                        details={"model": model_name, "error_body": err_body[:300]},
                    )
                elif http_err.code == 403:
                    raise GeminiVisionError(
                        GeminiErrorType.PERMISSION_DENIED,
                        "Insufficient permissions for Gemini API",
                        http_code=403,
                        details={"model": model_name, "error_body": err_body[:300]},
                    )
                elif http_err.code == 429:
                    cb.record_failure()
                    last_error = GeminiVisionError(
                        GeminiErrorType.QUOTA_EXHAUSTED,
                        f"Rate limited by Gemini API ({model_name})",
                        http_code=429,
                        details={"model": model_name},
                    )
                    # Continue to next retry attempt or next model
                    if attempt < 3:
                        logger.debug(f"Will retry {model_name} after backoff")
                    continue
                elif http_err.code == 404:
                    logger.warning(f"Model {model_name} not found (404)")
                    # Skip to next model
                    break
                else:
                    # Other 5xx/4xx errors
                    cb.record_failure()
                    raise GeminiVisionError(
                        GeminiErrorType.NETWORK_ERROR,
                        f"HTTP {http_err.code} from Gemini API",
                        http_code=http_err.code,
                        details={"model": model_name, "error_body": err_body[:300]},
                    )

            except asyncio.TimeoutError:
                logger.error(f"Timeout calling {model_name} (attempt {attempt}/3)")
                cb.record_failure()
                last_error = GeminiVisionError(
                    GeminiErrorType.TIMEOUT,
                    f"Gemini API call timed out (>{settings.gemini_vision_timeout_seconds}s)",
                    details={"model": model_name, "timeout_seconds": settings.gemini_vision_timeout_seconds},
                )
                if attempt < 3:
                    continue  # Retry
                # Fall through to try next model

            except Exception as exc:
                logger.error(
                    f"Gemini {model_name} failed (attempt {attempt}/3): {exc}\n{traceback.format_exc()}"
                )
                cb.record_failure()
                last_error = GeminiVisionError(
                    GeminiErrorType.NETWORK_ERROR,
                    f"Gemini API call failed: {str(exc)}",
                    details={"model": model_name, "exception": type(exc).__name__},
                )
                if attempt < 3:
                    continue  # Retry
                # Fall through to try next model

        # After all attempts for this model, continue to next model if available
        continue

    # All models and attempts exhausted
    if last_error:
        logger.error(
            f"All Gemini models exhausted. Final error: {last_error.error_type} - {last_error.message}"
        )
        raise last_error
    else:
        raise GeminiVisionError(
            GeminiErrorType.UNKNOWN,
            "All Gemini models unavailable or failed",
            details={"models_tried": _MODELS},
        )

