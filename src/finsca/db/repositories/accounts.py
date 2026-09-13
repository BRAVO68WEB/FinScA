from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.ids import new_id
from finsca.core.models import Account, AccountMonth, NewAccount, NewAccountMonth
from finsca.core.money import to_paise
from finsca.db import schema as tables
from finsca.db.mapping import account_from_row, dump_list, month_from_row, utcnow


class AmbiguousAccountError(ValueError):
    pass


def add(session: Session, payload: NewAccount) -> Account:
    now = utcnow()
    row = tables.Account(
        id=new_id(),
        display_name=payload.display_name,
        institution=payload.institution,
        type=payload.type.value,
        last4=payload.last4,
        upi_vpas=dump_list(payload.upi_vpas),
        holder_aliases=dump_list(payload.holder_aliases),
        currency=payload.currency,
        is_own=payload.is_own,
        credit_limit_paise=to_paise(payload.credit_limit) if payload.credit_limit is not None else None,
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
    by_id = session.get(tables.Account, needle)
    if by_id:
        return account_from_row(by_id)

    matches: list[tables.Account] = []
    for row in session.scalars(select(tables.Account)).all():
        account = account_from_row(row)
        aliases = {alias.casefold() for alias in account.holder_aliases}
        if (
            account.last4 == needle
            or account.display_name.casefold() == needle.casefold()
            or needle.casefold() in aliases
        ):
            matches.append(row)
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
    row.display_name = display_name.strip()
    row.updated_at = utcnow()
    session.flush()
    return account_from_row(row)


def add_alias(session: Session, account_id: str, alias: str) -> Account:
    row = session.get(tables.Account, account_id)
    if row is None:
        raise KeyError(account_id)
    account = account_from_row(row)
    label = alias.strip()
    if label and label not in account.holder_aliases:
        account.holder_aliases.append(label)
        row.holder_aliases = dump_list(account.holder_aliases)
        row.updated_at = utcnow()
        session.flush()
    return account_from_row(row)


def add_upi_vpa(session: Session, account_id: str, vpa: str) -> Account:
    row = session.get(tables.Account, account_id)
    if row is None:
        raise KeyError(account_id)
    account = account_from_row(row)
    value = vpa.strip()
    if value and value not in account.upi_vpas:
        account.upi_vpas.append(value)
        row.upi_vpas = dump_list(account.upi_vpas)
        row.updated_at = utcnow()
        session.flush()
    return account_from_row(row)


def upsert_month(session: Session, payload: NewAccountMonth) -> AccountMonth:
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
