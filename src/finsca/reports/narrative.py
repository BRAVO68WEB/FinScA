"""One paragraph over a month report that was already computed."""

from __future__ import annotations

from typing import Any, Callable

from finsca.core.money import format_inr
from finsca.llm.prompts.narrative import NARRATIVE_SYSTEM
from finsca.llm.router import reasoning_complete
from finsca.reports.monthly import MonthReport

CompleteFn = Callable[[list[dict[str, str]]], dict[str, Any] | None]


def month_narrative(report: MonthReport, *, complete: CompleteFn | None = None) -> str | None:
    fn = complete if complete is not None else reasoning_complete()
    if fn is None:
        return None
    try:
        raw = fn(
            [
                {"role": "system", "content": NARRATIVE_SYSTEM},
                {"role": "user", "content": _figures(report)},
            ]
        )
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    text = raw.get("narrative") or raw.get("answer")
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    return cleaned or None


def _figures(report: MonthReport) -> str:
    flow = report.flow
    rate = f"{flow.savings_rate:.0%}" if flow.savings_rate is not None else "n/a"
    categories = ", ".join(f"{name} {format_inr(amount)}" for name, amount in report.categories)
    parts = ", ".join(
        f"{key}={value if value is not None else 'n/a'}" for key, value in report.health.parts.items()
    )
    unlabeled = f"{report.unlabeled_share:.0%}" if report.unlabeled_share is not None else "n/a"
    return (
        f"month {report.year:04d}-{report.month:02d}\n"
        f"inflow {format_inr(flow.inflow)}\n"
        f"outflow {format_inr(flow.outflow)}\n"
        f"net {format_inr(flow.net)}\n"
        f"savings_rate {rate}\n"
        f"categories {categories}\n"
        f"health {report.health.score if report.health.score is not None else 'n/a'}\n"
        f"subscores {parts}\n"
        f"unlabeled {unlabeled}\n"
        f"emi_paid {format_inr(report.emi_paid)}\n"
        f"missed_emis {report.missed_emis}"
    )
