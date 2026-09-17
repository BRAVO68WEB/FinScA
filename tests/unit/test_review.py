from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.cli.app import app
from finsca.core.enums import AccountType, Channel, IncomeReview, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.apply import apply_rules, link_self_transfers

runner = CliRunner()


def _seed_pair(session: Session) -> tuple[Account, Account, Transaction, Transaction]:
    axis = account_repo.add(
        session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, institution="AXIS", last4="4004"),
    )
    icici = account_repo.add(
        session,
        Account(display_name="ICICI 0044", type=AccountType.SAVINGS, institution="ICICI", last4="0044"),
    )
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    debit, _ = tx_repo.add_event(
        session,
        Transaction(
            account_id=axis.id or "",
            posted_at=when,
            amount=Decimal("-56900.00"),
            description_raw="UPI/JYOTIRMOY/ICIC/653124283200",
            source_kind=SourceKind.PDF,
            channel=Channel.UPI,
            income_review=IncomeReview.SKIPPED,
        ),
    )
    credit, _ = tx_repo.add_event(
        session,
        Transaction(
            account_id=icici.id or "",
            posted_at=when + timedelta(hours=1),
            amount=Decimal("56900.00"),
            description_raw="UPI/AXIS BANK/653124283200",
            source_kind=SourceKind.PDF,
            channel=Channel.UPI,
        ),
    )
    return axis, icici, debit, credit


def test_link_marks_both_legs_self_transfer(db_session: Session) -> None:
    _, _, debit, credit = _seed_pair(db_session)
    assert credit.income_review is IncomeReview.PENDING
    assert link_self_transfers(db_session) == 1
    assert tx_repo.list_pending_review(db_session) == []
    left = tx_repo.get(db_session, debit.id or "")
    right = tx_repo.get(db_session, credit.id or "")
    assert left is not None and right is not None
    assert left.intent is Intent.SELF_TRANSFER
    assert right.intent is Intent.SELF_TRANSFER
    assert left.exclude_from_cashflow and right.exclude_from_cashflow
    assert left.self_transfer_group_id == right.self_transfer_group_id


def test_review_apply_income_and_remember_rule(data_dir: Path, db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="ICICI 0044", type=AccountType.SAVINGS, institution="ICICI", last4="0044"),
    )
    first, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
            amount=Decimal("104549.00"),
            description_raw="CMS/ CMS5656688195/V2V CYBERSECURITY PRIVATE LIMI",
            source_kind=SourceKind.PDF,
        ),
    )
    second, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 5, 29, tzinfo=timezone.utc),
            amount=Decimal("109132.00"),
            description_raw="CMS/ CMS5695847161/V2V CYBERSECURITY PRIVATE LIMI",
            source_kind=SourceKind.PDF,
        ),
    )
    db_session.commit()
    result = runner.invoke(
        app,
        [
            "review",
            "apply",
            (first.id or "")[:8],
            "income",
            "--category",
            "salary",
            "--always",
            "--match",
            "V2V CYBERSECURITY",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "income" in result.output
    with_db = runner.invoke(app, ["review", "link"])
    assert with_db.exit_code == 0, with_db.output
    # second credit should be auto-classified by the rule
    leftover = runner.invoke(app, ["review", "list"])
    assert leftover.exit_code == 0, leftover.output
    assert "no pending reviews" in leftover.output
    updated = tx_repo.get(db_session, second.id or "")
    assert updated is not None
    assert updated.intent is Intent.INCOME
    assert apply_rules(db_session) == 0


def test_credit_card_pending_is_hidden_and_closable(db_session: Session) -> None:
    card = account_repo.add(
        db_session,
        Account(display_name="ICICI CC 0003", type=AccountType.CREDIT_CARD, institution="ICICI", last4="0003"),
    )
    bank = account_repo.add(
        db_session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, institution="AXIS", last4="4004"),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=card.id or "",
            posted_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            amount=Decimal("7801.56"),
            description_raw="BBPS Payment received",
            source_kind=SourceKind.PDF,
        ),
    )
    bank_tx, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=bank.id or "",
            posted_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            amount=Decimal("12500.00"),
            description_raw="NEFT SALARY",
            source_kind=SourceKind.PDF,
        ),
    )
    pending = tx_repo.list_pending_review(db_session)
    assert [tx.id for tx in pending] == [bank_tx.id]
    assert tx_repo.close_credit_card_reviews(db_session) == 1
    closed = tx_repo.list_for_account(db_session, card.id or "")[0]
    assert closed.intent is Intent.TRANSFER
    assert closed.exclude_from_cashflow


def test_review_delete_removes_multiple_junk_rows(data_dir: Path, db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="HDFC 3628", type=AccountType.CREDIT_CARD, institution="HDFC", last4="3628"),
    )
    first, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
            amount=Decimal("300000.00"),
            description_raw="e Rs. 300000 loan option available",
            source_kind=SourceKind.EMAIL,
        ),
    )
    second, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
            amount=Decimal("300000.00"),
            description_raw="view this message in HTML format",
            source_kind=SourceKind.EMAIL,
        ),
    )
    db_session.commit()
    result = runner.invoke(
        app,
        ["review", "delete", (first.id or "")[:8], (second.id or "")[:8]],
    )
    assert result.exit_code == 0, result.output
    assert "removed 2" in result.output
    db_session.expire_all()
    assert tx_repo.get(db_session, first.id or "") is None
    assert tx_repo.get(db_session, second.id or "") is None
    leftover = runner.invoke(app, ["review", "list"])
    assert "no pending reviews" in leftover.output
