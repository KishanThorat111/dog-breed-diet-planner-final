"""
AI Provider Factory.

Single entry point for obtaining an AI provider.
For e2-micro deployment profile, only Gemini is registered.
"""
from __future__ import annotations

from typing import ClassVar

from app.ai.base import BaseAIProvider


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

    AIProviderFactory.register("gemini", GeminiProvider)


_register_defaults()


def get_provider(name: str | None = None) -> BaseAIProvider:
    """
    Return the provider for `name`, or the active provider from config if None.
    """
    from app.ai.config import get_ai_config

    cfg = get_ai_config()
    provider_name = name or cfg.active_provider

    return AIProviderFactory.get(provider_name)
