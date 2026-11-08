"""Record normalize/dedupe counts. Hashing already happened in persist."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, NormalizeInput, NormalizeOutput


class NormalizeAgent(Agent):
    name = "normalize"
    description = "Report how many rows were inserted and how many were duplicates."
    input_model = NormalizeInput
    output_model = NormalizeOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: NormalizeInput) -> AgentResult:
        del ctx
        return AgentResult(
            agent=self.name,
            output=NormalizeOutput(inserted=payload.inserted, dupes=payload.dupes),
        )


agent = NormalizeAgent()
