"""
OpenAI Provider.

Uses the openai async SDK (openai>=1.0).
Default model: gpt-4o-mini (cheapest capable OpenAI model).
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.base import AIRequest, AIResponse, BaseAIProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI via official async Python SDK.
    Lazy-initializes AsyncOpenAI on first use.
    """

    def __init__(self) -> None:
        self._client: Any | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def is_configured(self) -> bool:
        try:
            from app.config import settings
            return bool(getattr(settings, "openai_api_key", ""))
        except Exception:
            return False

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI  # type: ignore[import]
            except ImportError:
                raise RuntimeError(
                    "openai is not installed. Run: pip install openai"
                )
            from app.config import settings
            self._client = AsyncOpenAI(api_key=getattr(settings, "openai_api_key", ""))
        return self._client

    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_configured:
            raise RuntimeError("OpenAI: OPENAI_API_KEY is not set")

        from app.ai.config import get_ai_config
        cfg = get_ai_config()
        model_name = (
            request.metadata.get("model")
            or cfg.active_model
            or _DEFAULT_MODEL
        )

        client = self._get_client()

        with self._make_timer() as timer:
            kwargs: dict[str, Any] = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "timeout": request.timeout_seconds,
            }
            if request.json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = await client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return AIResponse(
            content=choice.message.content or "",
            provider="openai",
            model=model_name,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
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
                    json_mode=True,
                    metadata={"caller": "health_check"},
                )
            )
            return True, resp.latency_ms
        except Exception as exc:
            logger.debug("OpenAI health check failed: %s", exc)
            return False, 0
