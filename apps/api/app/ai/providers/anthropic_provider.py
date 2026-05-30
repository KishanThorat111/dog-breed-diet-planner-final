"""
Anthropic Claude Provider.

Uses the anthropic async SDK (anthropic>=0.40).
Default model: claude-3-haiku-20240307 (fastest, cheapest Claude).
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.base import AIRequest, AIResponse, BaseAIProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-3-haiku-20240307"


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude via official async Python SDK.
    Lazy-initializes AsyncAnthropic on first use.
    """

    def __init__(self) -> None:
        self._client: Any | None = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def is_configured(self) -> bool:
        try:
            from app.config import settings
            return bool(getattr(settings, "anthropic_api_key", ""))
        except Exception:
            return False

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic  # type: ignore[import]
            except ImportError:
                raise RuntimeError(
                    "anthropic is not installed. Run: pip install anthropic"
                )
            from app.config import settings
            self._client = AsyncAnthropic(api_key=getattr(settings, "anthropic_api_key", ""))
        return self._client

    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_configured:
            raise RuntimeError("Anthropic: ANTHROPIC_API_KEY is not set")

        from app.ai.config import get_ai_config
        cfg = get_ai_config()
        model_name = (
            request.metadata.get("model")
            or cfg.active_model
            or _DEFAULT_MODEL
        )

        client = self._get_client()

        with self._make_timer() as timer:
            # Anthropic uses a `system` top-level param (not in messages list)
            response = await client.messages.create(
                model=model_name,
                max_tokens=request.max_tokens,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.prompt}],
                temperature=request.temperature,
                timeout=request.timeout_seconds,
            )

        # Claude always returns text blocks
        content = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        usage = response.usage

        return AIResponse(
            content=content,
            provider="anthropic",
            model=model_name,
            prompt_tokens=usage.input_tokens if usage else 0,
            completion_tokens=usage.output_tokens if usage else 0,
            latency_ms=timer.elapsed_ms,
        )

    async def health_check(self) -> tuple[bool, int]:
        if not self.is_configured:
            return False, 0
        try:
            resp = await self.complete(
                AIRequest(
                    prompt='Respond with exactly: {"ok": true}',
                    max_tokens=20,
                    temperature=0,
                    timeout_seconds=8,
                    json_mode=False,  # Claude handles JSON via prompt
                    metadata={"caller": "health_check"},
                )
            )
            return True, resp.latency_ms
        except Exception as exc:
            logger.debug("Anthropic health check failed: %s", exc)
            return False, 0
