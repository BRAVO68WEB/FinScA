"""Cash-flow stage. Math stays in finance.cashflow."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import CashflowInput, CashflowOutput, IngestRunCtx
from finsca.finance.cashflow import cashflow


class CashflowAgent(Agent):
    name = "cashflow"
    description = "Inflow, outflow, and savings rate for a set of transactions."
    input_model = CashflowInput
    output_model = CashflowOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: CashflowInput) -> AgentResult:
        del ctx
        flow = cashflow(payload.transactions)
        return AgentResult(
            agent=self.name,
            output=CashflowOutput(
                inflow=flow.inflow,
                outflow=flow.outflow,
                net=flow.net,
                savings_rate=flow.savings_rate,
            ),
        )


agent = CashflowAgent()
