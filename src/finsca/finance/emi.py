"""Pure EMI calendar and match predicates."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timezone

from finsca.core.models import Loan, Transaction
from finsca.core.money import to_paise
from finsca.finance.normalize import normalize_description

_EMI_HINT = re.compile(r"\b(EMI|NACH|ACH|ECS|LOAN)\b")


def due_on(year: int, month: int, day: int | None) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day or 1, last))


def months_between(start: date, end: date) -> list[date]:
    cursor = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    months: list[date] = []
    while cursor <= stop:
        months.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def amount_matches(tx: Transaction, loan: Loan, *, tolerance: float = 0.02) -> bool:
    expected = to_paise(loan.emi)
    if expected <= 0 or tx.amount >= 0:
        return False
    actual = abs(to_paise(tx.amount))
    slack = max(100, int(expected * tolerance))
    return abs(actual - expected) <= slack


def day_matches(tx: Transaction, loan: Loan, *, window: int = 3) -> bool:
    if loan.emi_day is None:
        return True
    return abs(tx.posted_at.day - loan.emi_day) <= window


def looks_like_emi(description: str, lender: str) -> bool:
    blob = normalize_description(description)
    if _EMI_HINT.search(blob):
        return True
    return bool(lender) and lender.upper() in blob


def is_candidate(tx: Transaction, loan: Loan) -> bool:
    if tx.self_transfer_group_id:
        return False
    if loan.account_id and tx.account_id != loan.account_id:
        return False
    return amount_matches(tx, loan) and day_matches(tx, loan)


def as_due_datetime(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
