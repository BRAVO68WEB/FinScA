"""Rules, then YAML, then compact labels. Unknown stays unknown."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, LabelOutput, StageInput
from finsca.ledger.labeling import apply_labels


class LabelerAgent(Agent):
    name = "labeler"
    description = "Fill category and intent from rules, taxonomy, and the compact model."
    input_model = StageInput
    output_model = LabelOutput
    llm_tier = "compact"

    def run(self, ctx: IngestRunCtx, payload: StageInput) -> AgentResult:
        del payload
        counts = apply_labels(ctx.session, ctx.settings)
        return AgentResult(agent=self.name, output=LabelOutput(**counts))


agent = LabelerAgent()
