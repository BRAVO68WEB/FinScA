"""GST totals from stored gst_amount fields only (no silent inference)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finsca.core.models import Transaction
from finsca.finance.cashflow import is_spend


@dataclass(frozen=True)
class GstTotals:
    gst: Decimal
    taxable: Decimal
    rate: Decimal | None


def gst_totals(transactions: list[Transaction]) -> GstTotals:
    gst = Decimal("0.00")
    taxable = Decimal("0.00")
    for tx in transactions:
        if not is_spend(tx):
            continue
        if tx.gst_amount is None:
            continue
        gst += tx.gst_amount
        taxable += abs(tx.amount)
    rate = (gst / taxable) if taxable > 0 else None
    return GstTotals(gst=gst, taxable=taxable, rate=rate)
