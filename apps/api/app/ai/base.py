"""
AI Provider Abstraction Layer
=============================
All AI providers implement BaseAIProvider.
Business logic depends ONLY on these abstractions — never on a concrete provider.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIRequest:
    """Normalized input for any AI provider."""

    prompt: str
    system_prompt: str = (
        "You are a veterinary nutrition expert. "
        "Respond with valid JSON only. No markdown, no code fences."
    )
    max_tokens: int = 512
    temperature: float = 0.3
    timeout_seconds: int = 30
    # Tell providers that support it (Gemini, OpenAI) to return JSON natively
    json_mode: bool = True
    # Caller-supplied metadata passed through to observability logger
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Normalized output from any AI provider."""

    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cached: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseAIProvider(ABC):
    """
    Abstract base for all AI providers.

    Implementors must be:
    - Stateless (no per-request state stored on self)
    - Async-compatible (complete() is a coroutine)
    - Self-describing (provider_name, is_configured)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique slug: 'gemini' | 'openai' | 'anthropic'"""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True if the required API key is present and the SDK importable."""
        ...

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """
        Execute a completion request.
        Raises RuntimeError (or a subclass) on any failure.
        Never returns None.
        """
        ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, int]:
        """
        Lightweight connectivity probe.
        Returns (is_healthy, latency_ms).
        Should complete in < 5 seconds.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_timer() -> "_Timer":
        return _Timer()


class _Timer:
    """Simple wall-clock timer for latency measurement."""

    elapsed_ms: int = 0

    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)
