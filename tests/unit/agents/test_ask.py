from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.agents.orchestrator import answer_question
from finsca.cli.app import app
from finsca.config.settings import Settings
from finsca.core.enums import AccountType, Category, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo

runner = CliRunner()


def _seed_salary(db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, last4="4004"),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            amount=Decimal("80000.00"),
            description_raw="SALARY",
            source_kind=SourceKind.PDF,
            intent=Intent.INCOME,
            category=Category.SALARY,
        ),
    )
    db_session.commit()


def test_ask_without_a_provider_prints_no_amount(
    data_dir: Path,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("FINSCA_LLM_OFF", "1")
    _seed_salary(db_session)
    result = runner.invoke(app, ["ask", "how much did I earn"])
    assert result.exit_code == 0, result.output
    assert "ask needs an API key" in result.output
    assert "80000" not in result.output


def test_ask_without_a_tool_says_it_does_not_know(data_dir: Path, monkeypatch) -> None:
    def fake(_messages: list[dict[str, str]]) -> dict[str, str]:
        return {"answer": "You earned 80000.00"}

    monkeypatch.setattr("finsca.agents.orchestrator.reasoning_complete", lambda _settings: fake)
    result = runner.invoke(app, ["ask", "what did I earn"])
    assert result.exit_code == 0, result.output
    assert "I do not know." in result.output
    assert "80000" not in result.output


def test_ask_month_report_includes_the_tool_inflow(
    data_dir: Path,
    db_session: Session,
    monkeypatch,
) -> None:
    _seed_salary(db_session)

    def fake(messages: list[dict[str, str]]) -> dict[str, object]:
        if "tool_result" not in messages[-1]["content"]:
            return {"tool": "get_month_report", "arguments": {"year": 2026, "month": 8}}
        inflow = json.loads(messages[-1]["content"])["tool_result"]["flow"]["inflow"]
        return {"answer": f"Inflow was {inflow}"}

    monkeypatch.setattr("finsca.agents.orchestrator.reasoning_complete", lambda _settings: fake)
    result = runner.invoke(app, ["ask", "what was inflow in August"])
    assert result.exit_code == 0, result.output
    assert "80000.00" in result.output


def test_habits_is_not_a_subagent(data_dir: Path, db_session: Session) -> None:
    def fake(messages: list[dict[str, str]]) -> dict[str, object]:
        if "tool_result" not in messages[-1]["content"]:
            return {"tool": "run_subagent", "arguments": {"name": "habits"}}
        return {"answer": messages[-1]["content"]}

    text = answer_question(db_session, Settings(), "what are my habits", complete=fake)
    assert "unknown subagent habits" in text
