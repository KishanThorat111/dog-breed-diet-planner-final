"""
AI Provider Factory.

Single entry point for obtaining an AI provider.
Respects runtime config (active_provider + fallback_providers).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import ClassVar

from app.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """
    Registry of known providers.
    Providers are instantiated lazily and cached per provider name.
    """

    _registry: ClassVar[dict[str, type[BaseAIProvider]]] = {}
    _instances: ClassVar[dict[str, BaseAIProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseAIProvider]) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def get(cls, name: str) -> BaseAIProvider:
        """Return a cached instance for the named provider."""
        if name not in cls._instances:
            if name not in cls._registry:
                raise ValueError(
                    f"Unknown AI provider '{name}'. "
                    f"Available: {sorted(cls._registry)}"
                )
            cls._instances[name] = cls._registry[name]()
        return cls._instances[name]

    @classmethod
    def available_providers(cls) -> list[str]:
        return sorted(cls._registry)

    @classmethod
    def configured_providers(cls) -> list[str]:
        return [name for name in cls._registry if cls.get(name).is_configured]


# ------------------------------------------------------------------
# Register all built-in providers
# ------------------------------------------------------------------
def _register_defaults() -> None:
    from app.ai.providers.gemini import GeminiProvider
    from app.ai.providers.openai_provider import OpenAIProvider
    from app.ai.providers.anthropic_provider import AnthropicProvider

    AIProviderFactory.register("gemini", GeminiProvider)
    AIProviderFactory.register("openai", OpenAIProvider)
    AIProviderFactory.register("anthropic", AnthropicProvider)


_register_defaults()


def get_provider(name: str | None = None) -> BaseAIProvider:
    """
    Return the provider for `name`, or the active provider from config if None.
    Returns a FallbackAIProvider when the primary is not configured but
    fallback providers are available.
    """
    from app.ai.config import get_ai_config
    from app.ai.fallback import FallbackAIProvider

    cfg = get_ai_config()
    provider_name = name or cfg.active_provider

    primary = AIProviderFactory.get(provider_name)

    # If primary is configured and no fallbacks needed, return it directly
    if primary.is_configured and not cfg.fallback_providers:
        return primary

    # Build ordered chain: [primary] + fallbacks
    chain: list[BaseAIProvider] = [primary]
    for fb_name in cfg.fallback_providers:
        if fb_name != provider_name:
            try:
                chain.append(AIProviderFactory.get(fb_name))
            except ValueError:
                logger.warning("Unknown fallback provider: %s (skipped)", fb_name)

    return FallbackAIProvider(chain)
