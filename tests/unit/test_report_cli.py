from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.cli.app import app
from finsca.core.enums import AccountType, Category, Channel, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo

runner = CliRunner()


def test_report_prints_cashflow(data_dir: Path, db_session: Session) -> None:
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
            channel=Channel.NEFT,
        ),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
            amount=Decimal("-1200.00"),
            description_raw="SWIGGY",
            source_kind=SourceKind.PDF,
            intent=Intent.EXPENSE,
            category=Category.DINING,
            channel=Channel.UPI,
        ),
    )
    db_session.commit()
    result = runner.invoke(app, ["report", "--month", "2026-08"])
    assert result.exit_code == 0, result.output
    assert "80000.00" in result.output
    assert "1200.00" in result.output
    assert "dining" in result.output
    assert "health" in result.output
