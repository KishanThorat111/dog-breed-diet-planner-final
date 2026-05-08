"""
AI Diet Enrichment Service.

Augments rule-based diet plans with natural-language insights from an LLM.
The rule-based engine (diet_engine.py) is ALWAYS the source of truth for
nutritional numbers — the AI only adds explanatory text.

Design:
  - AI enrichment is OPTIONAL: if no provider is configured or AI is disabled,
    the plan is returned unchanged with ai_insights=None.
  - Results are cached in Redis by a hash of the input parameters so the same
    breed+age+weight+activity never calls the LLM twice.
  - Input is sanitized to prevent prompt injection from user-controlled fields.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from app.ai.base import AIRequest
from app.ai.config import get_ai_config
from app.ai.factory import get_provider

logger = logging.getLogger(__name__)

# Cached insights TTL: 24 hours (same breed/weight shouldn't change day-to-day)
_CACHE_TTL = 86_400

# Hard limit on string lengths included in prompt (prompt injection guard)
_MAX_FIELD_LEN = 80

# Allowed characters in free-text fields included in the prompt
_SAFE_PATTERN = re.compile(r"[^a-zA-Z0-9 \-_/,.()']+")


def _sanitize(value: str, max_len: int = _MAX_FIELD_LEN) -> str:
    """
    Strip characters outside the safe set and truncate.
    Prevents prompt injection from user-controlled fields
    (breed names, health conditions, etc.).
    """
    cleaned = _SAFE_PATTERN.sub("", value)
    return cleaned[:max_len].strip()


def _sanitize_list(items: list[str], max_items: int = 5) -> list[str]:
    return [_sanitize(item) for item in items[:max_items] if item]


def _cache_key(
    breed: str,
    age_months: int,
    weight_kg: float,
    activity_level: str,
    is_neutered: bool,
    supplement_flags: list[str],
) -> str:
    payload = json.dumps(
        {
            "b": breed[:50],
            "a": age_months,
            "w": round(weight_kg, 1),
            "l": activity_level,
            "n": is_neutered,
            "s": sorted(supplement_flags),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"ai_insights:{digest}"


def _build_prompt(
    breed: str,
    age_months: int,
    weight_kg: float,
    activity_level: str,
    is_neutered: bool,
    sex: str,
    daily_calories: int,
    protein_g: float,
    fat_g: float,
    supplement_flags: list[str],
    foods_to_avoid: list[str],
    health_conditions: list[str],
) -> str:
    """
    Build a compact, token-efficient prompt.
    All user-provided fields are sanitised before inclusion.
    """
    safe_breed = _sanitize(breed)
    safe_conditions = ", ".join(_sanitize_list(health_conditions)) or "none"
    safe_supplements = ", ".join(_sanitize_list(supplement_flags)) or "none"
    safe_avoid = ", ".join(_sanitize_list(foods_to_avoid, max_items=6)) or "none"

    life_stage = (
        "puppy" if age_months < 12
        else "senior" if age_months > 84
        else "adult"
    )
    neuter_str = "neutered/spayed" if is_neutered else "intact"

    return f"""Dog profile:
- Breed: {safe_breed}
- Age: {age_months} months ({life_stage})
- Weight: {weight_kg:.1f} kg
- Sex: {_sanitize(sex)} ({neuter_str})
- Activity: {_sanitize(activity_level)}
- Daily target: {daily_calories} kcal, {protein_g:.0f}g protein, {fat_g:.0f}g fat
- Supplements flagged: {safe_supplements}
- Foods to avoid: {safe_avoid}
- Health conditions: {safe_conditions}

Generate feeding insights as a JSON object with these exact keys:
{{
  "feeding_tip": "<1-2 sentence practical feeding advice for this dog>",
  "breed_note": "<1-2 sentence breed-specific nutrition consideration>",
  "label_tip": "<what to look for on commercial dog food labels for this dog>",
  "vet_note": "<one health concern to discuss with a vet, or null if none>"
}}"""


async def enrich_diet_plan(
    *,
    breed: str,
    age_months: int,
    weight_kg: float,
    activity_level: str,
    is_neutered: bool,
    sex: str,
    daily_calories: int,
    protein_g: float,
    fat_g: float,
    supplement_flags: list[str],
    foods_to_avoid: list[str],
    health_conditions: list[str],
) -> dict[str, Any] | None:
    """
    Return AI-generated diet insights for the given parameters, or None if:
      - AI is globally disabled (AI_ENABLED=false)
      - No provider is configured
      - The LLM call fails (all exceptions are swallowed — AI is non-critical)

    Result is cached in Redis to avoid duplicate LLM calls.
    """
    cfg = get_ai_config()
    if not cfg.enabled:
        return None

    provider = get_provider()
    if not provider.is_configured:
        logger.debug("AI enrichment skipped — no provider configured")
        return None

    # Check Redis cache first
    from app.utils.cache import cache

    key = _cache_key(breed, age_months, weight_kg, activity_level, is_neutered, supplement_flags)
    cached = await cache.get(key)
    if cached is not None:
        logger.debug("AI insights cache HIT key=%s", key)
        return cached

    # Build and send prompt
    prompt = _build_prompt(
        breed=breed,
        age_months=age_months,
        weight_kg=weight_kg,
        activity_level=activity_level,
        is_neutered=is_neutered,
        sex=sex,
        daily_calories=daily_calories,
        protein_g=protein_g,
        fat_g=fat_g,
        supplement_flags=supplement_flags,
        foods_to_avoid=foods_to_avoid,
        health_conditions=health_conditions,
    )

    request = AIRequest(
        prompt=prompt,
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        timeout_seconds=cfg.timeout_seconds,
        json_mode=True,
        metadata={"caller": "diet_enrichment", "breed": breed[:40]},
    )

    for attempt in range(1, cfg.max_retries + 1):
        try:
            response = await provider.complete(request)
            insights: dict[str, Any] = json.loads(response.content)

            # Validate expected keys exist (defensive)
            for key_name in ("feeding_tip", "breed_note", "label_tip"):
                if key_name not in insights:
                    insights[key_name] = ""

            # Store provider attribution (no key data — just provider/model name)
            insights["_provider"] = response.provider
            insights["_model"] = response.model

            # Cache the result
            await cache.set(key, insights, ttl_seconds=_CACHE_TTL)
            return insights

        except json.JSONDecodeError as exc:
            logger.warning("AI insights JSON parse failed (attempt %d): %s", attempt, exc)
        except Exception as exc:
            logger.warning(
                "AI enrichment failed (attempt %d/%d): %s",
                attempt, cfg.max_retries, exc,
            )

    # All attempts failed — return None (non-critical, plan still saved)
    return None
