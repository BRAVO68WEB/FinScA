"""Match EMI debits onto active loans."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import CountOutput, IngestRunCtx, StageInput
from finsca.ledger.loans import match_all


class LoanMatchAgent(Agent):
    name = "loans"
    description = "Attach this month's EMI debits to active loans."
    input_model = StageInput
    output_model = CountOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: StageInput) -> AgentResult:
        del payload
        return AgentResult(agent=self.name, output=CountOutput(count=match_all(ctx.session)))


agent = LoanMatchAgent()
