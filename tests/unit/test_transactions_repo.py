from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, Channel, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.repositories.transactions import DuplicateTransactionError


def _account(session: Session) -> Account:
    return account_repo.add(
        session,
        Account(display_name="HDFC", type=AccountType.SAVINGS, last4="4521"),
    )


def test_add_and_list_transactions(db_session: Session) -> None:
    account = _account(db_session)
    posted = datetime(2026, 8, 4, tzinfo=timezone.utc)
    created = tx_repo.add(
        db_session,
        Transaction(
            account_id=account.id,
            posted_at=posted,
            amount=Decimal("-250.00"),
            description_raw="UPI-SWIGGY",
            channel=Channel.UPI,
            source_kind=SourceKind.PDF,
        ),
    )
    assert created.amount == Decimal("-250.00")
    assert created.intent == Intent.UNKNOWN
    rows = tx_repo.list_for_account(db_session, account.id)
    assert len(rows) == 1
    assert rows[0].description_raw == "UPI-SWIGGY"


def test_find_transaction_by_content_hash(db_session: Session) -> None:
    account = _account(db_session)
    posted = datetime(2026, 8, 4, tzinfo=timezone.utc)
    first = tx_repo.add(
        db_session,
        Transaction(
            account_id=account.id,
            posted_at=posted,
            amount=Decimal("12500.00"),
            description_raw="NEFT SALARY",
            source_kind=SourceKind.PDF,
        ),
    )
    found = tx_repo.get_by_hash(db_session, first.content_hash)
    assert found is not None
    assert found.id == first.id


def test_duplicate_content_hash_rejected(db_session: Session) -> None:
    account = _account(db_session)
    payload = Transaction(
        account_id=account.id,
        posted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
        amount=Decimal("12500.00"),
        description_raw="NEFT SALARY",
        source_kind=SourceKind.PDF,
    )
    tx_repo.add(db_session, payload)
    with pytest.raises(DuplicateTransactionError):
        tx_repo.add(db_session, payload)
    assert len(tx_repo.list_for_account(db_session, account.id)) == 1
