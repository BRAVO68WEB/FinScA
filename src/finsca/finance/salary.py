"""Salary-cycle stats from salary-labeled credits."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date

from finsca.core.enums import Category
from finsca.core.models import Transaction


@dataclass(frozen=True)
class SalaryCycle:
    count: int
    modal_day: int | None
    last_paid: date | None
    regular: bool | None


def salary_cycle(transactions: list[Transaction]) -> SalaryCycle:
    pays = [
        tx
        for tx in transactions
        if tx.amount > 0 and tx.category is Category.SALARY
    ]
    if not pays:
        return SalaryCycle(count=0, modal_day=None, last_paid=None, regular=None)
    days = [tx.posted_at.day for tx in pays]
    modal = Counter(days).most_common(1)[0][0]
    last = max(tx.posted_at.date() for tx in pays)
    spread = max(days) - min(days)
    regular = spread <= 6
    return SalaryCycle(count=len(pays), modal_day=modal, last_paid=last, regular=regular)
