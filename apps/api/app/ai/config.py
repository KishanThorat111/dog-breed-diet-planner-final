"""
Runtime AI configuration.

Loaded from environment variables at process startup.
Can be updated at runtime via admin API (resets on process restart).
For permanent changes in production, update environment variables.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field


@dataclass
class AIConfig:
    """
    Single source of truth for active AI settings.
    One instance per process; mutated only through update_ai_config().
    """

    # Which provider handles new requests
    active_provider: str = "gemini"

    # Specific model. Defaults to the supported production primary.
    active_model: str | None = "gemini-2.5-flash"

    # Ordered fallback model chain for Gemini requests.
    fallback_models: list[str] = field(default_factory=lambda: ["gemini-2.5-flash-lite"])

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 512
    timeout_seconds: int = 30
    max_retries: int = 2

    # Kill-switch — False disables AI enrichment globally without removing keys
    enabled: bool = True

    def as_dict(self) -> dict:
        return {
            "active_provider": self.active_provider,
            "active_model": self.active_model,
            "fallback_models": list(self.fallback_models),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "enabled": self.enabled,
        }


_lock = threading.Lock()
_config = AIConfig()

# Field names allowed to be updated via admin API
_UPDATABLE_FIELDS = frozenset(AIConfig.__dataclass_fields__)  # type: ignore[attr-defined]


def _load_from_env() -> None:
    """Seed initial runtime config from environment variables."""
    with _lock:
        _config.active_provider = os.environ.get("AI_ACTIVE_PROVIDER", "gemini").lower()
        _config.active_model = os.environ.get("AI_ACTIVE_MODEL") or "gemini-2.5-flash"
        fallback_raw = os.environ.get("AI_FALLBACK_MODELS", "gemini-2.5-flash-lite")
        seen: set[str] = set()
        parsed_fallbacks: list[str] = []
        for item in fallback_raw.split(","):
            model = item.strip()
            if model and model != _config.active_model and model not in seen:
                seen.add(model)
                parsed_fallbacks.append(model)
        _config.fallback_models = parsed_fallbacks
        _config.enabled = os.environ.get("AI_ENABLED", "true").lower() not in ("false", "0", "no")


# Apply env seed at import time
_load_from_env()


def get_ai_config() -> AIConfig:
    """Return the current runtime config (read-only — do not mutate the object)."""
    return _config


def update_ai_config(**kwargs: object) -> AIConfig:
    """
    Update runtime config. Thread-safe.
    Unknown or read-only keys are silently ignored.
    """
    with _lock:
        for key, value in kwargs.items():
            if key in _UPDATABLE_FIELDS:
                setattr(_config, key, value)
    return _config
