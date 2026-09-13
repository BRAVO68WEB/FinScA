"""Spend-habit stats from labeled expenses."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from finsca.core.models import Transaction
from finsca.finance.cashflow import in_cashflow, is_spend


def top_categories(transactions: list[Transaction], *, limit: int = 6) -> list[tuple[str, Decimal]]:
    totals: Counter[str] = Counter()
    for tx in transactions:
        if not is_spend(tx):
            continue
        key = tx.category.value if tx.category else "unlabeled"
        totals[key] += abs(tx.amount)
    return totals.most_common(limit)


def unlabeled_share(transactions: list[Transaction]) -> Decimal | None:
    pool = [tx for tx in transactions if in_cashflow(tx) and tx.amount < 0]
    if not pool:
        return None
    unlabeled = sum(1 for tx in pool if tx.category is None)
    return (Decimal(unlabeled) / Decimal(len(pool))).quantize(Decimal("0.0001"))
