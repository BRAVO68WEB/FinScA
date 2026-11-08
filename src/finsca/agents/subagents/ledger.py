"""Persist one ParsedBatch: accounts, statement months, transactions."""

from __future__ import annotations

from finsca.agents.base import Agent, AgentResult
from finsca.agents.context import IngestRunCtx, PersistInput, PersistOutput
from finsca.ingest.persist import persist_batch


class LedgerAgent(Agent):
    name = "ledger"
    description = "Write a parsed batch onto the ledger."
    input_model = PersistInput
    output_model = PersistOutput
    llm_tier = "none"

    def run(self, ctx: IngestRunCtx, payload: PersistInput) -> AgentResult:
        saved = persist_batch(ctx.session, payload.batch, payload.run_id)
        return AgentResult(
            agent=self.name,
            output=PersistOutput(
                inserted=saved.inserted,
                dupes=saved.dupes,
                pending_review=saved.pending_review,
            ),
        )


agent = LedgerAgent()
