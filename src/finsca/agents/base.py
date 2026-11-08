"""Agent protocol. Subagents return structured results and do not call each other."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Tool(BaseModel):
    name: str
    description: str


class AgentResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent: str
    output: Any


class Agent:
    """One capability. ``llm_tier="none"`` means the stage does not call a model."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    tools: tuple[Tool, ...] = ()
    llm_tier: Literal["none", "compact", "openai", "grok"] = "none"

    def run(self, ctx: object, payload: BaseModel) -> AgentResult:
        raise NotImplementedError
