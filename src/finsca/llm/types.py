"""Shared LLM types."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Tier = Literal["grok", "openai", "compact"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class Completion(BaseModel):
    tier: Tier
    model: str
    data: dict[str, Any] = Field(default_factory=dict)
