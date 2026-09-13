"""Transparent health subscores. Missing inputs stay None and drop out of the total."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finsca.finance.cashflow import Cashflow


@dataclass(frozen=True)
class Health:
    score: int | None
    parts: dict[str, int | None]


def _band(value: Decimal | None, *, good: Decimal, bad: Decimal, invert: bool = False) -> int | None:
    if value is None:
        return None
    if invert:
        if value <= good:
            return 100
        if value >= bad:
            return 0
        span = bad - good
        return int(100 * (bad - value) / span)
    if value >= good:
        return 100
    if value <= bad:
        return 0
    span = good - bad
    return int(100 * (value - bad) / span)


def health_score(
    *,
    flow: Cashflow,
    emi_to_income: Decimal | None,
    cc_util: Decimal | None,
    emergency_months: Decimal | None,
    salary_regular: bool | None,
    unlabeled: Decimal | None,
    missed_emis: int,
) -> Health:
    parts: dict[str, int | None] = {
        "savings_rate": _band(flow.savings_rate, good=Decimal("0.20"), bad=Decimal("0")),
        "emi_income": _band(emi_to_income, good=Decimal("0.20"), bad=Decimal("0.50"), invert=True),
        "cc_util": _band(cc_util, good=Decimal("0.30"), bad=Decimal("0.80"), invert=True),
        "emergency": _band(emergency_months, good=Decimal("6"), bad=Decimal("0")),
        "salary": None if salary_regular is None else (100 if salary_regular else 40),
        "unlabeled": _band(
            (Decimal("1") - unlabeled) if unlabeled is not None else None,
            good=Decimal("0.85"),
            bad=Decimal("0.40"),
        ),
        "missed_emi": 100 if missed_emis == 0 else max(0, 100 - 25 * missed_emis),
    }
    weights = {
        "savings_rate": 25,
        "emi_income": 20,
        "cc_util": 15,
        "emergency": 15,
        "salary": 10,
        "unlabeled": 10,
        "missed_emi": 5,
    }
    usable = {key: weights[key] for key, value in parts.items() if value is not None}
    if not usable:
        return Health(score=None, parts=parts)
    total_w = sum(usable.values())
    score = sum(parts[key] * usable[key] for key in usable) / total_w
    return Health(score=int(round(score)), parts=parts)
