"""
AI Request Observability.

Logs every AI request with provider, model, latency, token usage, and outcome.
Feeds Sentry on errors and provides structured logs for Railway/Datadog.
"""
from __future__ import annotations

import logging
from typing import Any

from app.ai.base import AIRequest, AIResponse

logger = logging.getLogger("app.ai")


def log_request(
    *,
    request: AIRequest,
    response: AIResponse | None = None,
    error: Exception | None = None,
    attempt: int = 1,
) -> None:
    """Emit a structured log line for every AI call attempt."""
    ctx: dict[str, Any] = {
        "provider": response.provider if response else request.metadata.get("target_provider", "?"),
        "model": response.model if response else "?",
        "prompt_tokens": response.prompt_tokens if response else 0,
        "completion_tokens": response.completion_tokens if response else 0,
        "latency_ms": response.latency_ms if response else 0,
        "cached": response.cached if response else False,
        "attempt": attempt,
        "caller": request.metadata.get("caller", "unknown"),
    }

    if error:
        logger.warning(
            "AI request FAILED provider=%s attempt=%d error=%s",
            ctx["provider"],
            attempt,
            error,
            extra=ctx,
        )
    else:
        logger.info(
            "AI request OK provider=%s model=%s latency=%dms tokens=%d+%d cached=%s",
            ctx["provider"],
            ctx["model"],
            ctx["latency_ms"],
            ctx["prompt_tokens"],
            ctx["completion_tokens"],
            ctx["cached"],
            extra=ctx,
        )
