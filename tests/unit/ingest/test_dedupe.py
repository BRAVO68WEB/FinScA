from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, Channel, SourceKind
from finsca.core.models import Account
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.ingest.persist import persist_batch
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine


def test_sms_and_pdf_same_upi_is_one_row(db_session: Session) -> None:
    account_repo.add(
        db_session,
        Account(display_name="HDFC 4521", type=AccountType.SAVINGS, institution="HDFC", last4="4521"),
    )
    posted = datetime(2026, 8, 1, tzinfo=timezone.utc)
    pdf = persist_batch(
        db_session,
        ParsedBatch(
            parser="hdfc",
            source_kind=SourceKind.PDF,
            account=AccountHint(last4="4521", institution="HDFC"),
            lines=[
                ParsedLine(
                    posted_at=posted,
                    amount=Decimal("-250.00"),
                    description="UPI-SWIGGY",
                    channel=Channel.UPI,
                )
            ],
        ),
        run_id="pdf",
    )
    sms = persist_batch(
        db_session,
        ParsedBatch(
            parser="sms",
            source_kind=SourceKind.SMS,
            lines=[
                ParsedLine(
                    posted_at=posted,
                    amount=Decimal("-250.00"),
                    description="SWIGGY via UPI",
                    channel=Channel.UPI,
                    last4="4521",
                    institution="HDFC",
                )
            ],
        ),
        run_id="sms",
    )
    assert pdf.inserted == 1
    assert sms.inserted == 0
    assert sms.dupes == 1
    account = account_repo.list_by_last4(db_session, "4521")[0]
    rows = tx_repo.list_for_account(db_session, account.id)
    assert len(rows) == 1
    assert rows[0].amount == Decimal("-250.00")
    assert "sms" in (rows[0].source_ref or "")
