"""Inflow / outflow from labeled intents. Transfers and unknowns stay out."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finsca.core.enums import Category, Intent
from finsca.core.models import Transaction

_INFLOW = {Intent.INCOME, Intent.LOAN_DISBURSAL, Intent.REFUND}
_OUTFLOW = {Intent.EXPENSE, Intent.EMI, Intent.INVESTMENT}


@dataclass(frozen=True)
class Cashflow:
    inflow: Decimal
    outflow: Decimal
    refunds: Decimal
    net: Decimal
    savings_rate: Decimal | None


def in_cashflow(tx: Transaction) -> bool:
    if tx.exclude_from_cashflow:
        return False
    return tx.intent not in {Intent.TRANSFER, Intent.SELF_TRANSFER}


def is_inflow(tx: Transaction) -> bool:
    return in_cashflow(tx) and tx.intent in _INFLOW


def is_outflow(tx: Transaction) -> bool:
    if not in_cashflow(tx):
        return False
    if tx.intent in _OUTFLOW:
        return True
    return tx.category is Category.TAX_GST


def is_spend(tx: Transaction) -> bool:
    return in_cashflow(tx) and tx.amount < 0 and tx.intent is Intent.EXPENSE


def cashflow(transactions: list[Transaction]) -> Cashflow:
    inflow = outflow = refunds = Decimal("0.00")
    for tx in transactions:
        if tx.intent is Intent.REFUND and in_cashflow(tx):
            refunds += tx.amount
        if is_inflow(tx):
            inflow += tx.amount
        elif is_outflow(tx):
            outflow += abs(tx.amount)
    net = inflow - outflow
    rate = (net / inflow) if inflow > 0 else None
    return Cashflow(inflow=inflow, outflow=outflow, refunds=refunds, net=net, savings_rate=rate)
