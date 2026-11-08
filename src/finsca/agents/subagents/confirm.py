"""Apply stored income/transfer rules. Does not invent new decisions."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import CountOutput, IngestRunCtx, StageInput
from finsca.ledger.apply import apply_rules


class ConfirmAgent(Agent):
    name = "confirm"
    description = "Apply review rules already stored on the ledger."
    input_model = StageInput
    output_model = CountOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: StageInput) -> AgentResult:
        del payload
        return AgentResult(agent=self.name, output=CountOutput(count=apply_rules(ctx.session)))


agent = ConfirmAgent()
