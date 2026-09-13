"""Spend-habit stats from expense-like debits."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from finsca.core.enums import Intent
from finsca.core.models import Transaction
from finsca.finance.cashflow import in_cashflow


def expense_txs(transactions: list[Transaction]) -> list[Transaction]:
    return [
        tx
        for tx in transactions
        if in_cashflow(tx) and tx.amount < 0 and tx.intent in {Intent.EXPENSE, Intent.UNKNOWN, Intent.EMI}
    ]


def top_categories(transactions: list[Transaction], *, limit: int = 6) -> list[tuple[str, Decimal]]:
    totals: Counter[str] = Counter()
    for tx in expense_txs(transactions):
        key = tx.category.value if tx.category else "unlabeled"
        totals[key] += abs(tx.amount)
    return totals.most_common(limit)


def unlabeled_share(transactions: list[Transaction]) -> Decimal | None:
    expenses = expense_txs(transactions)
    if not expenses:
        return None
    unlabeled = sum(1 for tx in expenses if tx.category is None)
    return (Decimal(unlabeled) / Decimal(len(expenses))).quantize(Decimal("0.0001"))
