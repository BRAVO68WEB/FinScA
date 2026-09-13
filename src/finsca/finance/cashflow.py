"""Inflow / outflow from labeled intents. Transfers are excluded."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finsca.core.enums import Intent
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


def cashflow(transactions: list[Transaction]) -> Cashflow:
    inflow = outflow = refunds = Decimal("0.00")
    for tx in transactions:
        if not in_cashflow(tx):
            continue
        if tx.intent is Intent.REFUND:
            refunds += tx.amount
        if tx.intent in _INFLOW:
            inflow += tx.amount
        elif tx.intent in _OUTFLOW or (tx.intent is Intent.UNKNOWN and tx.amount < 0):
            outflow += abs(tx.amount)
    net = inflow - outflow
    rate = (net / inflow) if inflow > 0 else None
    return Cashflow(inflow=inflow, outflow=outflow, refunds=refunds, net=net, savings_rate=rate)
