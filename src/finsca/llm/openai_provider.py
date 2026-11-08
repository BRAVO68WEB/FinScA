"""OpenAI chat completions. Message text is redacted before it leaves the process."""

from __future__ import annotations

import json
from typing import Any

from finsca.llm.redaction import redact


class OpenAIProvider:
    def __init__(self, api_key: str, model: str, *, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def complete(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        *,
        client: Any = None,
    ) -> dict[str, Any]:
        outgoing = [_redacted(message) for message in messages]
        if schema is not None:
            outgoing.append({"role": "system", "content": "JSON schema: " + json.dumps(schema)})
        created = client or self._client()
        response = created.chat.completions.create(
            model=self.model,
            messages=outgoing,
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}

    def _client(self) -> Any:
        from openai import OpenAI

        if self.base_url:
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        return OpenAI(api_key=self.api_key)


def _redacted(message: dict[str, str]) -> dict[str, str]:
    return {"role": message.get("role", "user"), "content": redact(message.get("content", ""))}
