from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finsca.core.clock import utcnow
from finsca.core.enums import MonthSource
from finsca.core.ids import new_id
from finsca.core.models import Account, AccountMonth
from finsca.core.money import to_paise
from finsca.db import schema as tables
from finsca.db.mapping import account_from_row, month_from_row


class AmbiguousAccountError(ValueError):
    pass


class StatementProtectedError(ValueError):
    def __init__(self, month: AccountMonth) -> None:
        self.month = month
        super().__init__(
            f"{month.year:04d}-{month.month:02d} is a statement month; "
            "computed values cannot overwrite it"
        )


def add(session: Session, account: Account) -> Account:
    now = utcnow()
    row = tables.Account(
        id=new_id(),
        display_name=account.display_name,
        institution=account.institution,
        type=account.type.value,
        last4=account.last4,
        upi_vpas=list(account.upi_vpas),
        holder_aliases=list(account.holder_aliases),
        currency=account.currency,
        is_own=account.is_own,
        credit_limit_paise=to_paise(account.credit_limit) if account.credit_limit is not None else None,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return account_from_row(row)


def get(session: Session, account_id: str) -> Account | None:
    row = session.get(tables.Account, account_id)
    return account_from_row(row) if row else None


def list_all(session: Session) -> list[Account]:
    rows = session.scalars(select(tables.Account).order_by(tables.Account.display_name)).all()
    return [account_from_row(row) for row in rows]


def resolve(session: Session, token: str) -> Account | None:
    needle = token.strip()
    if not needle:
        return None

    exact = session.get(tables.Account, needle)
    if exact is not None:
        return account_from_row(exact)

    found: dict[str, tables.Account] = {}

    def absorb(rows: list[tables.Account]) -> None:
        for row in rows:
            found[row.id] = row

    absorb(list(session.scalars(select(tables.Account).where(tables.Account.id.startswith(needle)))))
    absorb(list(session.scalars(select(tables.Account).where(tables.Account.last4 == needle))))
    absorb(
        list(
            session.scalars(
                select(tables.Account).where(func.lower(tables.Account.display_name) == needle.casefold())
            )
        )
    )
    folded = needle.casefold()
    for row in session.scalars(select(tables.Account)):
        aliases = [alias.casefold() for alias in (row.holder_aliases or [])]
        if folded in aliases:
            found[row.id] = row

    matches = list(found.values())
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(row.display_name for row in matches)
        raise AmbiguousAccountError(f"account {token!r} matches more than one row: {names}")
    return account_from_row(matches[0])


def rename(session: Session, account_id: str, display_name: str) -> Account:
    row = session.get(tables.Account, account_id)
    if row is None:
        raise KeyError(account_id)
    name = Account(display_name=display_name, type=row.type).display_name
    row.display_name = name
    row.updated_at = utcnow()
    session.flush()
    return account_from_row(row)


def _append_unique(session: Session, account_id: str, field: str, value: str) -> Account:
    row = session.get(tables.Account, account_id)
    if row is None:
        raise KeyError(account_id)
    label = value.strip()
    current = list(getattr(row, field) or [])
    if label and label not in current:
        setattr(row, field, current + [label])
        row.updated_at = utcnow()
        session.flush()
    return account_from_row(row)


def add_alias(session: Session, account_id: str, alias: str) -> Account:
    return _append_unique(session, account_id, "holder_aliases", alias)


def add_upi_vpa(session: Session, account_id: str, vpa: str) -> Account:
    return _append_unique(session, account_id, "upi_vpas", vpa)


def set_month(session: Session, payload: AccountMonth, *, force: bool = False) -> AccountMonth:
    existing = session.scalar(
        select(tables.AccountMonth).where(
            tables.AccountMonth.account_id == payload.account_id,
            tables.AccountMonth.year == payload.year,
            tables.AccountMonth.month == payload.month,
        )
    )
    if existing is None:
        row = tables.AccountMonth(
            id=new_id(),
            account_id=payload.account_id,
            year=payload.year,
            month=payload.month,
            opening_paise=to_paise(payload.opening),
            closing_paise=to_paise(payload.closing),
            source=payload.source.value,
            statement_id=payload.statement_id,
        )
        session.add(row)
        session.flush()
        return month_from_row(row)

    if (
        not force
        and existing.source == MonthSource.STATEMENT.value
        and payload.source is MonthSource.COMPUTED
    ):
        raise StatementProtectedError(month_from_row(existing))

    existing.opening_paise = to_paise(payload.opening)
    existing.closing_paise = to_paise(payload.closing)
    existing.source = payload.source.value
    existing.statement_id = payload.statement_id
    session.flush()
    return month_from_row(existing)


def list_months(
    session: Session,
    account_id: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> list[AccountMonth]:
    stmt = select(tables.AccountMonth).order_by(
        tables.AccountMonth.year, tables.AccountMonth.month, tables.AccountMonth.account_id
    )
    if account_id:
        stmt = stmt.where(tables.AccountMonth.account_id == account_id)
    if year is not None:
        stmt = stmt.where(tables.AccountMonth.year == year)
    if month is not None:
        stmt = stmt.where(tables.AccountMonth.month == month)
    return [month_from_row(row) for row in session.scalars(stmt).all()]
