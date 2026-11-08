"""Health score from subscores that were already computed."""

from __future__ import annotations

from decimal import Decimal

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import HealthInput, HealthOutput, IngestRunCtx
from finsca.finance.cashflow import Cashflow
from finsca.finance.health import health_score


class HealthAgent(Agent):
    name = "health"
    description = "Financial health score from cash-flow and loan inputs."
    input_model = HealthInput
    output_model = HealthOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: HealthInput) -> AgentResult:
        del ctx
        flow = Cashflow(
            inflow=payload.inflow,
            outflow=payload.outflow,
            refunds=Decimal("0"),
            net=payload.inflow - payload.outflow,
            savings_rate=payload.savings_rate,
        )
        scored = health_score(
            flow=flow,
            emi_to_income=payload.emi_to_income,
            cc_util=payload.cc_util,
            emergency_months=payload.emergency_months,
            salary_regular=payload.salary_regular,
            unlabeled=payload.unlabeled,
            missed_emis=payload.missed_emis,
        )
        return AgentResult(
            agent=self.name,
            output=HealthOutput(score=scored.score, parts=scored.parts),
        )


agent = HealthAgent()
