"""Write a standalone HTML copy of a month report."""

from __future__ import annotations

from html import escape
from pathlib import Path

from finsca.core.money import format_inr
from finsca.reports.monthly import MonthReport


def write_html(report: MonthReport, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    flow = report.flow
    rate = f"{flow.savings_rate:.0%}" if flow.savings_rate is not None else "n/a"
    health = str(report.health.score) if report.health.score is not None else "n/a"
    cats = "".join(
        f"<tr><td>{escape(name)}</td><td>{format_inr(amount)}</td></tr>"
        for name, amount in report.categories
    )
    dest.write_text(
        (
            f"<html><body><h1>FinScA {report.year:04d}-{report.month:02d}</h1>"
            f"<p>In {format_inr(flow.inflow)} / Out {format_inr(flow.outflow)} / "
            f"Net {format_inr(flow.net)} / Savings {rate}</p>"
            f"<p>Health {health} / unlabeled {report.unlabeled_share}</p>"
            f"<table>{cats}</table></body></html>"
        ),
        encoding="utf-8",
    )
    return dest
