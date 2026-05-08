"""
Fallback AI Provider.

Tries providers in order; automatically falls back on any exception.
Implements the same BaseAIProvider interface so callers are unaware of fallback.
"""
from __future__ import annotations

import logging

from app.ai.base import AIRequest, AIResponse, BaseAIProvider
from app.ai.observability import log_request

logger = logging.getLogger(__name__)


class FallbackAIProvider(BaseAIProvider):
    """
    Wraps an ordered list of providers. Tries each in sequence, moving to
    the next whenever one raises an exception.

    Example chain: [GeminiProvider, OpenAIProvider, AnthropicProvider]
      → Gemini fails → tries OpenAI → if OK, returns OpenAI response
    """

    def __init__(self, providers: list[BaseAIProvider]) -> None:
        if not providers:
            raise ValueError("FallbackAIProvider requires at least one provider")
        self._providers = providers

    @property
    def provider_name(self) -> str:
        # Report as the primary (first) provider
        return self._providers[0].provider_name

    @property
    def is_configured(self) -> bool:
        return any(p.is_configured for p in self._providers)

    async def complete(self, request: AIRequest) -> AIResponse:
        last_exc: Exception | None = None

        for attempt, provider in enumerate(self._providers, start=1):
            if not provider.is_configured:
                logger.debug(
                    "Skipping %s (not configured)", provider.provider_name
                )
                continue

            try:
                # Tag the request with which provider we're targeting
                tagged = AIRequest(
                    **{
                        **request.__dict__,
                        "metadata": {
                            **request.metadata,
                            "target_provider": provider.provider_name,
                        },
                    }
                )
                response = await provider.complete(tagged)
                log_request(request=tagged, response=response, attempt=attempt)
                return response

            except Exception as exc:
                last_exc = exc
                log_request(
                    request=request, error=exc, attempt=attempt
                )
                logger.warning(
                    "Provider %s failed (attempt %d/%d): %s — trying next",
                    provider.provider_name,
                    attempt,
                    len(self._providers),
                    exc,
                )

        raise RuntimeError(
            f"All AI providers exhausted. Last error: {last_exc}"
        ) from last_exc

    async def health_check(self) -> tuple[bool, int]:
        # Report healthy if ANY provider is healthy
        for provider in self._providers:
            if provider.is_configured:
                ok, latency = await provider.health_check()
                if ok:
                    return True, latency
        return False, 0
