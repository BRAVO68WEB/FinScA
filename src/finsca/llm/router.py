"""Optional compact completions. Missing keys or FINSCA_LLM_OFF → no callable."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from finsca.config.settings import Settings

CompleteFn = Callable[[list[dict[str, str]]], dict[str, Any]]


def compact_complete(settings: Settings | None = None) -> CompleteFn | None:
    cfg = settings or Settings()
    if cfg.llm_off:
        return None
    if cfg.compact_provider == "grok":
        if not os.environ.get("XAI_API_KEY"):
            return None
    elif not os.environ.get("OPENAI_API_KEY"):
        return None

    def _call(messages: list[dict[str, str]]) -> dict[str, Any]:
        return _request(messages, cfg)

    return _call


def _request(messages: list[dict[str, str]], cfg: Settings) -> dict[str, Any]:
    from openai import OpenAI

    if cfg.compact_provider == "grok":
        client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
        model = cfg.compact_model if "grok" in cfg.compact_model else cfg.grok_model
    else:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = cfg.compact_model
    response = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    return parsed if isinstance(parsed, dict) else {"labels": []}
