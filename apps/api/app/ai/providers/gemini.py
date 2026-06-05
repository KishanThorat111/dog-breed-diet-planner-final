"""
Google Gemini AI Provider.

Uses google-generativeai SDK.
Primary model: gemini-2.5-flash.
Fallback model: gemini-2.5-flash-lite.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ai.base import AIRequest, AIResponse, BaseAIProvider

logger = logging.getLogger(__name__)

_PRIMARY_MODEL = "gemini-2.5-flash"
_FALLBACK_MODELS = ("gemini-2.5-flash-lite",)


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

    @staticmethod
    def _candidate_models(
        request: AIRequest,
        configured_model: str | None,
        fallback_models: list[str] | tuple[str, ...] | None,
    ) -> list[str]:
        """
        Build model attempts in priority order without duplicates.

        Order:
        1) per-request override
        2) runtime configured model
        3) stable primary
        4) stable fallbacks
        """
        requested = request.metadata.get("model")
        models: list[str] = []
        effective_fallbacks = tuple(fallback_models or _FALLBACK_MODELS)
        for name in (requested, configured_model, _PRIMARY_MODEL, *effective_fallbacks):
            if isinstance(name, str) and name and name not in models:
                models.append(name)
        return models

    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_configured:
            raise RuntimeError("Gemini: GEMINI_API_KEY is not set")

        from app.ai.config import get_ai_config
        cfg = get_ai_config()
        model_names = self._candidate_models(request, cfg.active_model, getattr(cfg, "fallback_models", None))
        if not model_names:
            raise RuntimeError("Gemini: no model configured")

        genai = self._get_sdk()
        last_exc: Exception | None = None

        for attempt, model_name in enumerate(model_names, start=1):
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
                except asyncio.TimeoutError as exc:
                    last_exc = RuntimeError(
                        f"Gemini timed out after {request.timeout_seconds}s (model={model_name})"
                    )
                    logger.warning(
                        "Gemini model attempt %d/%d timed out: %s",
                        attempt,
                        len(model_names),
                        model_name,
                    )
                    continue
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "Gemini model attempt %d/%d failed: %s (%s)",
                        attempt,
                        len(model_names),
                        model_name,
                        exc,
                    )
                    continue

            usage = getattr(response, "usage_metadata", None)
            return AIResponse(
                content=response.text,
                provider="gemini",
                model=model_name,
                prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
                completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
                latency_ms=timer.elapsed_ms,
            )

        raise RuntimeError(
            f"Gemini failed for all configured models {model_names}. Last error: {last_exc}"
        ) from last_exc

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
                    metadata={"caller": "health_check", "model": _PRIMARY_MODEL},
                )
            )
            return True, resp.latency_ms
        except Exception as exc:
            logger.debug("Gemini health check failed: %s", exc)
            return False, 0
