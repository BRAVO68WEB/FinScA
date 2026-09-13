"""Optional compact completions. Missing keys or FINSCA_LLM_OFF → None."""

from __future__ import annotations

import json
import os
from typing import Any

from finsca.config.settings import Settings


def compact_available(settings: Settings) -> bool:
    if settings.llm_off:
        return False
    if settings.compact_provider == "grok":
        return bool(os.environ.get("XAI_API_KEY"))
    return bool(os.environ.get("OPENAI_API_KEY"))


def complete_compact(messages: list[dict[str, str]], settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or Settings()
    if not compact_available(cfg):
        return {"labels": []}
    from openai import OpenAI

    if cfg.compact_provider == "grok":
        client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
        model = cfg.grok_model
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
