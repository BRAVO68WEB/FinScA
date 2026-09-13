from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, Channel, MonthSource, SourceKind
from finsca.core.models import Account
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ingest.errors import ParseError
from finsca.ingest.persist import persist_batch
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine


def _batch() -> ParsedBatch:
    return ParsedBatch(
        parser="generic",
        account=AccountHint(last4="4521", institution="HDFC", display_name="HDFC 4521"),
        period_start=datetime(2026, 8, 1).date(),
        period_end=datetime(2026, 8, 31).date(),
        opening=Decimal("10000.00"),
        closing=Decimal("22250.00"),
        lines=[
            ParsedLine(
                posted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                amount=Decimal("-250.00"),
                description="UPI-SWIGGY",
                channel=Channel.UPI,
            ),
            ParsedLine(
                posted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
                amount=Decimal("12500.00"),
                description="NEFT SALARY",
                channel=Channel.NEFT,
            ),
        ],
    )


def test_persist_creates_account_month_and_txs(db_session: Session) -> None:
    result = persist_batch(db_session, _batch(), run_id="run1")
    assert result.inserted == 2
    assert result.pending_review == 1
    account = account_repo.list_by_last4(db_session, "4521")[0]
    months = account_repo.list_months(db_session, account_id=account.id)
    assert len(months) == 1
    assert months[0].source == MonthSource.STATEMENT
    assert months[0].closing == Decimal("22250.00")
    txs = tx_repo.list_for_account(db_session, account.id)
    assert len(txs) == 2
    assert txs[0].source_kind == SourceKind.PDF


def test_persist_reuses_existing_account_and_dedupes(db_session: Session) -> None:
    existing = account_repo.add(
        db_session,
        Account(display_name="HDFC Salary", type=AccountType.SAVINGS, institution="HDFC", last4="4521"),
    )
    persist_batch(db_session, _batch(), run_id="run1")
    second = persist_batch(db_session, _batch(), run_id="run2")
    assert second.dupes == 2
    assert second.inserted == 0
    assert len(tx_repo.list_for_account(db_session, existing.id)) == 2


def test_persist_requires_last4(db_session: Session) -> None:
    batch = _batch()
    batch.account.last4 = None
    with pytest.raises(ParseError, match="last4"):
        persist_batch(db_session, batch, run_id="run1")
    assert account_repo.list_all(db_session) == []
