"""Task tier → provider. Missing keys or FINSCA_LLM_OFF → no call."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from finsca.config.settings import Settings
from finsca.llm.grok_provider import GrokProvider
from finsca.llm.openai_provider import OpenAIProvider
from finsca.llm.types import Tier

CompleteFn = Callable[[list[dict[str, str]]], dict[str, Any]]


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def complete(
        self,
        tier: Tier,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        provider = self.provider_for(tier)
        if provider is None:
            return None
        return provider.complete(messages, schema)

    def provider_for(self, tier: Tier) -> OpenAIProvider | None:
        if self.settings.llm_off:
            return None
        if tier == "compact":
            return _compact_provider(self.settings)
        if tier == "openai" or (
            tier == "grok" and self.settings.reasoning_provider == "openai"
        ):
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                return None
            return OpenAIProvider(key, self.settings.openai_model)
        key = os.environ.get("XAI_API_KEY")
        if not key:
            return None
        return GrokProvider(key, self.settings.grok_model)


def reasoning_complete(settings: Settings | None = None) -> CompleteFn | None:
    """Callable for ask and the month narrative. None when that tier cannot run."""
    router = LLMRouter(settings)
    tier: Tier = "openai" if router.settings.reasoning_provider == "openai" else "grok"
    if router.provider_for(tier) is None:
        return None

    def _call(messages: list[dict[str, str]]) -> dict[str, Any]:
        parsed = router.complete(tier, messages)
        return parsed if isinstance(parsed, dict) else {}

    return _call


def compact_complete(settings: Settings | None = None) -> CompleteFn | None:
    """Callable for the labeler. None when the compact tier cannot run."""
    router = LLMRouter(settings)

    def _call(messages: list[dict[str, str]]) -> dict[str, Any]:
        parsed = router.complete("compact", messages)
        return parsed if isinstance(parsed, dict) else {"labels": []}

    if router.provider_for("compact") is None:
        return None
    return _call


def _compact_provider(cfg: Settings) -> OpenAIProvider | None:
    if cfg.compact_provider == "grok":
        key = os.environ.get("XAI_API_KEY")
        if not key:
            return None
        model = cfg.compact_model if "grok" in cfg.compact_model else cfg.grok_model
        return GrokProvider(key, model)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAIProvider(key, cfg.compact_model)
