"""SMS ingest. Dump loaders stay in ingest.sms."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, ParseInput, ParseOutput
from finsca.core.enums import SourceKind
from finsca.ingest.dispatch import parse_inbox_file
from finsca.ingest.errors import ParseError


class SmsIngestAgent(Agent):
    name = "ingest_sms"
    description = "Parse one SMS dump into alert lines."
    input_model = ParseInput
    output_model = ParseOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: ParseInput) -> AgentResult:
        if payload.kind is not SourceKind.SMS:
            raise ParseError(f"ingest_sms got {payload.kind}")
        batch = parse_inbox_file(payload.path, payload.kind, ctx.settings)
        return AgentResult(agent=self.name, output=ParseOutput(batch=batch))


agent = SmsIngestAgent()
