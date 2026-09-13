from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.cli.app import app
from finsca.core.enums import AccountType, Channel, EmiStatus, Intent, SourceKind
from finsca.core.models import Account, Loan, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import loans as loan_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.loans import add_loan

runner = CliRunner()


def test_add_loan_matches_existing_debit(db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="HDFC 4521", type=AccountType.SAVINGS, last4="4521", institution="HDFC"),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 4, 5, tzinfo=timezone.utc),
            amount=Decimal("-18420.00"),
            description_raw="NACH EMI HDFC HOME",
            source_kind=SourceKind.PDF,
            channel=Channel.NACH,
        ),
    )
    loan = add_loan(
        db_session,
        Loan(
            name="HDFC Home",
            lender="HDFC",
            principal=Decimal("2500000"),
            emi=Decimal("18420.00"),
            emi_day=5,
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            account_id=account.id,
        ),
    )
    occ = loan_repo.list_occurrences(db_session, loan.id or "")
    paid = [item for item in occ if item.status is EmiStatus.PAID]
    assert len(paid) == 1
    labeled = tx_repo.get(db_session, paid[0].transaction_id or "")
    assert labeled is not None
    assert labeled.intent is Intent.EMI


def test_loans_cli_add_and_list(data_dir: Path) -> None:
    added = runner.invoke(
        app,
        [
            "loans",
            "add",
            "--name",
            "Car",
            "--lender",
            "AXIS",
            "--emi",
            "12500",
            "--day",
            "10",
            "--start",
            "2026-08-01",
        ],
    )
    assert added.exit_code == 0, added.output
    listed = runner.invoke(app, ["loans", "list"])
    assert listed.exit_code == 0, listed.output
    assert "Car" in listed.output
    assert "12500.00" in listed.output
