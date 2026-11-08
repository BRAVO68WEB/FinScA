"""The spec agents exist and call the functions that already own the work."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from finsca.agents.context import CashflowInput, HealthInput, StageInput
from finsca.agents.registry import get, names
from finsca.core.enums import Intent, SourceKind
from finsca.core.models import Transaction
from finsca.ingest.pdf.generic_llm import parse_unknown_statement
from finsca.ingest.sms.fallback import parse_unmatched


SPEC_AGENTS = {
    "ingest_pdf",
    "ingest_email",
    "ingest_sms",
    "normalize",
    "labeler",
    "confirm",
    "ledger",
    "cashflow",
    "loans",
    "health",
    "archive",
    "report",
}


def test_registry_lists_spec_agents() -> None:
    assert SPEC_AGENTS <= set(names())


def test_parse_agents_do_not_call_a_model() -> None:
    for name in ("ingest_pdf", "ingest_email", "ingest_sms", "ledger", "archive", "confirm"):
        assert get(name).llm_tier == "none"
    assert get("labeler").llm_tier == "compact"


def test_unknown_agent_names_the_registry() -> None:
    with pytest.raises(KeyError, match="unknown agent"):
        get("missing")


def test_cashflow_agent_uses_finance_cashflow() -> None:
    tx = Transaction(
        account_id="acct",
        posted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        amount=Decimal("100.00"),
        description_raw="SALARY",
        source_kind=SourceKind.PDF,
        intent=Intent.INCOME,
    )
    result = get("cashflow").run(ctx=None, payload=CashflowInput(transactions=[tx]))  # type: ignore[arg-type]
    assert result.output.inflow == Decimal("100.00")
    assert result.output.outflow == Decimal("0")


def test_health_agent_scores_a_savings_rate() -> None:
    result = get("health").run(
        ctx=None,  # type: ignore[arg-type]
        payload=HealthInput(
            inflow=Decimal("100"),
            outflow=Decimal("50"),
            savings_rate=Decimal("0.50"),
            missed_emis=0,
        ),
    )
    assert result.agent == "health"
    assert result.output.score is not None
    assert result.output.parts["savings"] == 100


def test_confirm_agent_accepts_stage_input() -> None:
    assert get("confirm").input_model is StageInput


def test_parsers_return_nothing_when_the_router_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSCA_LLM_OFF", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    assert parse_unmatched("Rs.10 debited") is None
    assert parse_unknown_statement("Statement of account") is None
