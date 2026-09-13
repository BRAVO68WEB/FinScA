from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from finsca.core.enums import AccountType, Channel, SourceKind
from finsca.core.models import Account, Transaction
from finsca.finance.self_transfer import find_pairs


def _account(account_id: str, last4: str, institution: str) -> Account:
    return Account(
        id=account_id,
        display_name=f"{institution} {last4}",
        type=AccountType.SAVINGS,
        institution=institution,
        last4=last4,
        is_own=True,
    )


def _tx(
    tx_id: str,
    account_id: str,
    amount: str,
    when: datetime,
    desc: str,
) -> Transaction:
    return Transaction(
        id=tx_id,
        account_id=account_id,
        posted_at=when,
        amount=Decimal(amount),
        description_raw=desc,
        source_kind=SourceKind.PDF,
        channel=Channel.UPI,
    )


def test_pairs_opposite_legs_on_own_accounts() -> None:
    axis = _account("a1", "4004", "AXIS")
    icici = _account("a2", "0044", "ICICI")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    debit = _tx("d1", "a1", "-56900.00", when, "UPI/JYOTIRMOY/ICIC/Paid via/ 653124283200")
    credit = _tx("c1", "a2", "56900.00", when + timedelta(hours=1), "UPI/AXIS BANK/653124283200")
    pairs = find_pairs([debit, credit], [axis, icici])
    assert len(pairs) == 1
    assert pairs[0].debit_id == "d1"
    assert pairs[0].credit_id == "c1"


def test_does_not_pair_same_account() -> None:
    axis = _account("a1", "4004", "AXIS")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    pairs = find_pairs(
        [
            _tx("d1", "a1", "-100.00", when, "UPI OUT"),
            _tx("c1", "a1", "100.00", when, "UPI IN"),
        ],
        [axis],
    )
    assert pairs == []


def test_does_not_pair_outside_window() -> None:
    axis = _account("a1", "4004", "AXIS")
    icici = _account("a2", "0044", "ICICI")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    pairs = find_pairs(
        [
            _tx("d1", "a1", "-100.00", when, "UPI OUT"),
            _tx("c1", "a2", "100.00", when + timedelta(days=5), "UPI IN"),
        ],
        [axis, icici],
        window_hours=72,
    )
    assert pairs == []


def test_unique_candidate_pairs_without_ref() -> None:
    axis = _account("a1", "4004", "AXIS")
    icici = _account("a2", "0044", "ICICI")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    pairs = find_pairs(
        [
            _tx("d1", "a1", "-100.00", when, "UPI OUT"),
            _tx("c1", "a2", "100.00", when, "UPI IN"),
        ],
        [axis, icici],
    )
    assert len(pairs) == 1


def test_last4_picks_among_multiple_candidates() -> None:
    a = _account("a1", "4004", "AXIS")
    b = _account("a2", "0044", "ICICI")
    c = _account("a3", "9033", "IDFC")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    pairs = find_pairs(
        [
            _tx("d1", "a1", "-100.00", when, "UPI to 0044"),
            _tx("c1", "a2", "100.00", when, "UPI IN ICICI"),
            _tx("c2", "a3", "100.00", when, "UPI IN IDFC"),
        ],
        [a, b, c],
    )
    assert len(pairs) == 1
    assert pairs[0].credit_id == "c1"


def test_ambiguous_same_amount_without_signal_is_skipped() -> None:
    a = _account("a1", "4004", "AXIS")
    b = _account("a2", "0044", "ICICI")
    c = _account("a3", "9033", "IDFC")
    when = datetime(2026, 6, 14, tzinfo=timezone.utc)
    pairs = find_pairs(
        [
            _tx("d1", "a1", "-100.00", when, "UPI OUT"),
            _tx("c1", "a2", "100.00", when, "UPI IN ONE"),
            _tx("c2", "a3", "100.00", when, "UPI IN TWO"),
        ],
        [a, b, c],
    )
    assert pairs == []
