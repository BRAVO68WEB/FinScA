from __future__ import annotations

from decimal import Decimal

import pytest

from finsca.finance.cashflow import Cashflow
from finsca.finance.gst import GstTotals
from finsca.finance.health import Health
from finsca.finance.salary import SalaryCycle
from finsca.reports.monthly import MonthReport
from finsca.reports.narrative import month_narrative


def _report() -> MonthReport:
    return MonthReport(
        year=2026,
        month=8,
        flow=Cashflow(
            inflow=Decimal("80000.00"),
            outflow=Decimal("1200.00"),
            refunds=Decimal("0"),
            net=Decimal("78800.00"),
            savings_rate=Decimal("0.985"),
        ),
        categories=[("dining", Decimal("1200.00"))],
        channels=[],
        salary=SalaryCycle(count=1, modal_day=1, last_paid=None, regular=True),
        gst=GstTotals(gst=Decimal("0"), taxable=Decimal("0"), rate=None),
        health=Health(score=80, parts={"savings": 40, "emi": None}),
        emi_paid=Decimal("0"),
        missed_emis=0,
        unlabeled_share=Decimal("0"),
    )


def test_narrative_returns_the_paragraph_and_sends_figures_only() -> None:
    seen: dict[str, str] = {}

    def fake(messages: list[dict[str, str]]) -> dict[str, str]:
        seen["user"] = messages[-1]["content"]
        return {"narrative": "Savings is the weak spot and dining is one category."}

    text = month_narrative(_report(), complete=fake)
    assert text == "Savings is the weak spot and dining is one category."
    assert "80000.00" in seen["user"]
    assert "dining" in seen["user"]
    assert "1200.00" in seen["user"]
    assert "SWIGGY" not in seen["user"]


def test_narrative_is_silent_when_the_router_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINSCA_LLM_OFF", "1")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    assert month_narrative(_report()) is None
