"""PDF ingest. Bytes stay in ingest.pdf; this agent only returns a ParsedBatch."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, ParseInput, ParseOutput
from finsca.core.enums import SourceKind
from finsca.ingest.dispatch import parse_inbox_file
from finsca.ingest.errors import ParseError


class PdfIngestAgent(Agent):
    name = "ingest_pdf"
    description = "Parse one statement or card PDF into a ParsedBatch."
    input_model = ParseInput
    output_model = ParseOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: ParseInput) -> AgentResult:
        if payload.kind is not SourceKind.PDF:
            raise ParseError(f"ingest_pdf got {payload.kind}")
        batch = parse_inbox_file(payload.path, payload.kind, ctx.settings)
        return AgentResult(agent=self.name, output=ParseOutput(batch=batch))


agent = PdfIngestAgent()
