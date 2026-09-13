from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from finsca.core.enums import Channel, SourceKind
from finsca.core.models import Loan, Transaction
from finsca.finance.emi import amount_matches, day_matches, looks_like_emi, months_between


def test_months_between_inclusive() -> None:
    months = months_between(date(2026, 3, 15), date(2026, 6, 1))
    assert [item.month for item in months] == [3, 4, 5, 6]


def test_amount_and_day_windows() -> None:
    loan = Loan(name="X", lender="HDFC", principal=Decimal("100000"), emi=Decimal("18420.00"), emi_day=5)
    tx = Transaction(
        account_id="a1",
        posted_at=datetime(2026, 4, 6, tzinfo=timezone.utc),
        amount=Decimal("-18420.00"),
        description_raw="NACH EMI HDFC",
        source_kind=SourceKind.PDF,
        channel=Channel.NACH,
    )
    assert amount_matches(tx, loan)
    assert day_matches(tx, loan)
    assert looks_like_emi(tx.description_raw)
    assert not looks_like_emi("UPI/Paid via C/HDFC/same amount")
    far = tx.model_copy(update={"posted_at": datetime(2026, 4, 20, tzinfo=timezone.utc)})
    assert not day_matches(far, loan)
