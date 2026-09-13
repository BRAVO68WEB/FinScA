from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, Channel, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.bills import inject_cc_bills


def test_inject_marks_cred_as_self_transfer(db_session: Session) -> None:
    bank = account_repo.add(
        db_session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, last4="4004", institution="AXIS"),
    )
    tx, _ = tx_repo.add_event(
        db_session,
        Transaction(
            account_id=bank.id or "",
            posted_at=datetime(2026, 4, 6, tzinfo=timezone.utc),
            amount=Decimal("-145899.06"),
            description_raw="UPI/P2M/609635402980/CRED Club /paymen/AXIS BANK",
            source_kind=SourceKind.PDF,
            channel=Channel.UPI,
        ),
    )
    assert inject_cc_bills(db_session) == 1
    assert inject_cc_bills(db_session) == 0
    updated = tx_repo.get(db_session, tx.id or "")
    assert updated is not None
    assert updated.intent is Intent.SELF_TRANSFER
    assert updated.exclude_from_cashflow
    cards = [item for item in account_repo.list_all(db_session) if item.type is AccountType.CREDIT_CARD]
    assert len(cards) == 1
    assert cards[0].institution == "CRED"
