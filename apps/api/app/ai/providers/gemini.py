"""
Google Gemini AI Provider.

Uses google-generativeai SDK.
Default model: gemini-1.5-flash (free tier: 15 RPM, 1M tokens/day).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ai.base import AIRequest, AIResponse, BaseAIProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-1.5-flash"
_HEALTH_PROMPT = '{"ping": true}'


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini via google-generativeai SDK.
    Lazy-initializes the SDK on first use — the import only happens
    if the provider is actually called, not at module load time.
    """

    def __init__(self) -> None:
        self._genai: Any | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_configured(self) -> bool:
        try:
            from app.config import settings
            return bool(settings.gemini_api_key)
        except Exception:
            return False

    def _get_sdk(self) -> Any:
        """Lazy-import and configure the google-generativeai SDK."""
        if self._genai is None:
            try:
                import google.generativeai as genai  # type: ignore[import]
            except ImportError:
                raise RuntimeError(
                    "google-generativeai is not installed. "
                    "Run: pip install google-generativeai"
                )
            from app.config import settings
            genai.configure(api_key=settings.gemini_api_key)
            self._genai = genai
        return self._genai

    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_configured:
            raise RuntimeError("Gemini: GEMINI_API_KEY is not set")

        from app.ai.config import get_ai_config
        cfg = get_ai_config()
        model_name = (
            request.metadata.get("model")  # per-request override
            or cfg.active_model            # admin runtime override
            or _DEFAULT_MODEL
        )

        genai = self._get_sdk()

        with self._make_timer() as timer:
            try:
                gen_config = genai.types.GenerationConfig(
                    temperature=request.temperature,
                    max_output_tokens=request.max_tokens,
                    response_mime_type="application/json" if request.json_mode else "text/plain",
                )
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=request.system_prompt,
                    generation_config=gen_config,
                )

                # google-generativeai SDK is synchronous — run in executor
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, model.generate_content, request.prompt),
                    timeout=request.timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"Gemini timed out after {request.timeout_seconds}s"
                )

        usage = getattr(response, "usage_metadata", None)
        return AIResponse(
            content=response.text,
            provider="gemini",
            model=model_name,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
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
            logger.debug("Gemini health check failed: %s", exc)
            return False, 0
