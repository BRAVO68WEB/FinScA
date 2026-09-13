from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from finsca.core.enums import AccountType, MonthSource
from finsca.core.models import NewAccount, NewAccountMonth
from finsca.db.repositories import accounts as account_repo


def test_add_and_get_account(db_session: Session) -> None:
    created = account_repo.add(
        db_session,
        NewAccount(
            display_name="HDFC Salary",
            type=AccountType.SAVINGS,
            institution="HDFC",
            last4="4521",
            holder_aliases=["salary"],
        ),
    )
    fetched = account_repo.get(db_session, created.id)
    assert fetched is not None
    assert fetched.display_name == "HDFC Salary"
    assert fetched.last4 == "4521"
    assert fetched.holder_aliases == ["salary"]
    assert fetched.currency == "INR"


def test_list_and_resolve_by_last4(db_session: Session) -> None:
    account_repo.add(
        db_session,
        NewAccount(display_name="HDFC Salary", type=AccountType.SAVINGS, last4="4521"),
    )
    listed = account_repo.list_all(db_session)
    assert len(listed) == 1
    resolved = account_repo.resolve(db_session, "4521")
    assert resolved is not None
    assert resolved.display_name == "HDFC Salary"


def test_add_alias_and_rename(db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        NewAccount(display_name="Old", type=AccountType.SAVINGS, last4="1111"),
    )
    account_repo.add_alias(db_session, account.id, "pocket")
    account_repo.rename(db_session, account.id, "New")
    updated = account_repo.get(db_session, account.id)
    assert updated is not None
    assert updated.display_name == "New"
    assert "pocket" in updated.holder_aliases


def test_upsert_account_month(db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        NewAccount(display_name="HDFC", type=AccountType.SAVINGS, last4="4521"),
    )
    month = account_repo.upsert_month(
        db_session,
        NewAccountMonth(
            account_id=account.id,
            year=2026,
            month=8,
            opening=Decimal("10000.00"),
            closing=Decimal("12500.50"),
            source=MonthSource.COMPUTED,
        ),
    )
    again = account_repo.upsert_month(
        db_session,
        NewAccountMonth(
            account_id=account.id,
            year=2026,
            month=8,
            opening=Decimal("10000.00"),
            closing=Decimal("13000.00"),
            source=MonthSource.STATEMENT,
        ),
    )
    assert month.id == again.id
    stored = account_repo.list_months(db_session, account_id=account.id)
    assert len(stored) == 1
    assert stored[0].closing == Decimal("13000.00")
    assert stored[0].source == MonthSource.STATEMENT
