"""xAI / Grok via the OpenAI-compatible API."""

from __future__ import annotations

from finsca.llm.openai_provider import OpenAIProvider

XAI_BASE_URL = "https://api.x.ai/v1"


class GrokProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model, base_url=XAI_BASE_URL)
