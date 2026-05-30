"""
Runtime AI configuration.

Loaded from environment variables at process startup.
Can be updated at runtime via admin API (resets on process restart).
For permanent changes in production, update environment variables.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass


@dataclass
class AIConfig:
    """
    Single source of truth for active AI settings.
    One instance per process; mutated only through update_ai_config().
    """

    # Which provider handles new requests
    active_provider: str = "gemini"

    # Specific model; None = provider default (cheapest/fastest)
    active_model: str | None = None

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
        _config.active_model = os.environ.get("AI_ACTIVE_MODEL") or None
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
