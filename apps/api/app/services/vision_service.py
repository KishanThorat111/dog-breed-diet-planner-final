"""
AI Vision Breed Classification Service.

Uses Gemini Vision (or OpenAI Vision as fallback) to identify dog breeds
from images with high accuracy.

Falls back to the local EfficientNet ML model when no AI key is configured.
"""
from __future__ import annotations

import json
import logging
import re
from difflib import get_close_matches
from typing import Any

logger = logging.getLogger(__name__)

# Prompt that grounds Gemini to our 120-breed taxonomy
_CLASSIFY_PROMPT = """\
You are a world-class canine expert and dog breed identification system.

Examine the image carefully and identify the dog breed with maximum precision.

Respond with ONLY a valid JSON object — no markdown, no explanation — in this exact format:
{
  "is_dog": true,
  "top_breed_key": "golden_retriever",
  "top_display_name": "Golden Retriever",
  "top_confidence": 0.97,
  "predictions": [
    {"breed_key": "golden_retriever", "display_name": "Golden Retriever", "confidence": 0.97},
    {"breed_key": "labrador_retriever", "display_name": "Labrador Retriever", "confidence": 0.02},
    {"breed_key": "chesapeake_bay_retriever", "display_name": "Chesapeake Bay Retriever", "confidence": 0.01}
  ]
}

Rules:
- "is_dog" must be true if the image shows a dog, false otherwise.
- Use ONLY breed_key values from this list (snake_case):
  chihuahua, japanese_spaniel, maltese, pekinese, shih_tzu, blenheim_spaniel,
  papillon, toy_terrier, rhodesian_ridgeback, afghan_hound, basset, beagle,
  bloodhound, bluetick, black_and_tan_coonhound, walker_hound, english_foxhound,
  redbone, borzoi, irish_wolfhound, italian_greyhound, whippet, ibizan_hound,
  norwegian_elkhound, otterhound, saluki, scottish_deerhound, weimaraner,
  staffordshire_bullterrier, american_staffordshire_terrier, bedlington_terrier,
  border_terrier, kerry_blue_terrier, irish_terrier, norfolk_terrier, norwich_terrier,
  yorkshire_terrier, wire_haired_fox_terrier, lakeland_terrier, sealyham_terrier,
  airedale, cairn, australian_terrier, dandie_dinmont, boston_bull,
  miniature_schnauzer, giant_schnauzer, standard_schnauzer, scotch_terrier,
  tibetan_terrier, silky_terrier, soft_coated_wheaten_terrier,
  west_highland_white_terrier, lhasa, flat_coated_retriever, curly_coated_retriever,
  golden_retriever, labrador_retriever, chesapeake_bay_retriever,
  german_short_haired_pointer, vizsla, english_setter, irish_setter, gordon_setter,
  brittany_spaniel, clumber, english_springer, welsh_springer_spaniel,
  cocker_spaniel, sussex_spaniel, irish_water_spaniel, kuvasz, schipperke,
  groenendael, malinois, briard, kelpie, komondor, old_english_sheepdog,
  shetland_sheepdog, collie, border_collie, bouvier_des_flandres, rottweiler,
  german_shepherd, doberman, miniature_pinscher, greater_swiss_mountain_dog,
  bernese_mountain_dog, appenzeller, entlebucher, boxer, bull_mastiff,
  tibetan_mastiff, french_bulldog, great_dane, saint_bernard, eskimo_dog,
  malamute, siberian_husky, affenpinscher, basenji, pug, leonberg, newfoundland,
  great_pyrenees, samoyed, pomeranian, chow, keeshond, brabancon_griffon,
  pembroke, cardigan, toy_poodle, miniature_poodle, standard_poodle,
  mexican_hairless, dingo, dhole, african_hunting_dog
- If the exact breed is not in the list, pick the closest match.
- top_confidence must be between 0.0 and 1.0.
- Include 3-5 predictions, sorted by confidence descending.
"""


def _parse_gemini_response(text: str) -> dict[str, Any] | None:
    """Extract and parse the JSON from Gemini's response."""
    try:
        # Strip potential markdown code fences
        cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse Gemini vision response: %r", text[:200])
        return None


def _map_to_known_breed(breed_key: str) -> "BreedInfo | None":
    """Map a Gemini-returned key to a known BreedInfo, with fuzzy fallback."""
    from app.ml.breed_labels import KEY_TO_BREED, BREED_LIST
    if breed_key in KEY_TO_BREED:
        return KEY_TO_BREED[breed_key]
    all_keys = list(KEY_TO_BREED.keys())
    matches = get_close_matches(breed_key, all_keys, n=1, cutoff=0.6)
    if matches:
        logger.info("Fuzzy-matched breed '%s' → '%s'", breed_key, matches[0])
        return KEY_TO_BREED[matches[0]]
    return None


async def classify_breed_with_gemini(
    image_bytes: bytes,
    content_type: str,
) -> dict[str, Any] | None:
    """
    Send image to Gemini Vision and return structured breed classification.
    Returns None if Gemini is not configured or the call fails.
    """
    from app.config import settings
    if not settings.gemini_api_key:
        logger.debug("Gemini API key not set — skipping vision classification.")
        return None

    try:
        import google.generativeai as genai  # type: ignore[import]
        genai.configure(api_key=settings.gemini_api_key)

        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            generation_config=genai.types.GenerationConfig(
                temperature=0.05,          # Near-deterministic output
                max_output_tokens=512,
                response_mime_type="application/json",
            ),
        )

        response = model.generate_content(
            contents=[
                _CLASSIFY_PROMPT,
                {"mime_type": content_type, "data": image_bytes},
            ]
        )
        raw_text: str = response.text or ""
    except Exception as exc:
        logger.error("Gemini vision call failed: %s", exc)
        return None

    data = _parse_gemini_response(raw_text)
    if not data:
        return None

    if not data.get("is_dog", True):
        logger.info("Gemini says image is not a dog.")
        return None  # Let pipeline handle non-dog gracefully

    top_key = data.get("top_breed_key", "")
    top_info = _map_to_known_breed(top_key)

    # Build predictions list
    from app.ml.breed_labels import KEY_TO_BREED, BreedInfo
    predictions = []
    for p in data.get("predictions", []):
        key = p.get("breed_key", "")
        info = _map_to_known_breed(key)
        if info:
            predictions.append({
                "breed": info.key,
                "display_name": info.display_name,
                "confidence": float(p.get("confidence", 0.0)),
                "size": info.size,
            })

    # If top info couldn't be resolved, use first prediction
    if not top_info and predictions:
        top_key = predictions[0]["breed"]
        top_info = _map_to_known_breed(top_key)

    if not top_info or not predictions:
        logger.warning("Gemini returned unresolvable breed: %r", top_key)
        return None

    return {
        "top_breed": top_info.key,
        "top_display_name": top_info.display_name,
        "top_confidence": float(data.get("top_confidence", predictions[0]["confidence"])),
        "all_predictions": predictions,
        "provider": "gemini-vision",
    }
