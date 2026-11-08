"""Assemble one month report from the ledger."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, ReportInput, ReportOutput
from finsca.ledger.report import report_for


class ReportAgent(Agent):
    name = "report"
    description = "Build the monthly cash-flow report DTO."
    input_model = ReportInput
    output_model = ReportOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: ReportInput) -> AgentResult:
        report = report_for(ctx.session, payload.year, payload.month)
        return AgentResult(agent=self.name, output=ReportOutput(report=report))


agent = ReportAgent()
