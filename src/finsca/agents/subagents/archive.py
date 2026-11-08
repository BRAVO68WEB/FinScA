"""Move successfully parsed inbox files into the run archive."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import ArchiveInput, ArchiveOutput, IngestRunCtx
from finsca.archive.mover import archive_successes


class ArchiveAgent(Agent):
    name = "archive"
    description = "Move parsed inbox files into data/archive and write manifest.json."
    input_model = ArchiveInput
    output_model = ArchiveOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: ArchiveInput) -> AgentResult:
        del ctx
        moved = archive_successes(payload.files, payload.dest, payload.run_id)
        return AgentResult(agent=self.name, output=ArchiveOutput(files=moved))


agent = ArchiveAgent()
