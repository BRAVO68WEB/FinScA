from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from finsca.core.enums import Category, Channel, EmiStatus, Intent, SourceKind
from finsca.core.models import EmiOccurrence, Transaction
from finsca.finance.cashflow import cashflow
from finsca.finance.health import health_score
from finsca.reports.monthly import build_report


def _tx(amount: str, intent: Intent, **kwargs) -> Transaction:
    return Transaction(
        account_id="a1",
        posted_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        amount=Decimal(amount),
        description_raw=kwargs.get("desc", "x"),
        source_kind=SourceKind.PDF,
        channel=kwargs.get("channel", Channel.UPI),
        intent=intent,
        category=kwargs.get("category"),
        exclude_from_cashflow=kwargs.get("exclude", False),
    )


def test_cashflow_excludes_self_transfer() -> None:
    txs = [
        _tx("100000.00", Intent.INCOME, category=Category.SALARY),
        _tx("-20000.00", Intent.EXPENSE, category=Category.DINING),
        _tx("-50000.00", Intent.SELF_TRANSFER),
        _tx("50000.00", Intent.SELF_TRANSFER),
    ]
    flow = cashflow(txs)
    assert flow.inflow == Decimal("100000.00")
    assert flow.outflow == Decimal("20000.00")
    assert flow.net == Decimal("80000.00")
    assert flow.savings_rate == Decimal("0.8")


def test_health_uses_savings_rate() -> None:
    flow = cashflow([_tx("100000", Intent.INCOME), _tx("-20000", Intent.EXPENSE)])
    result = health_score(
        flow=flow,
        emi_to_income=Decimal("0.10"),
        cc_util=None,
        emergency_months=Decimal("8"),
        salary_regular=True,
        unlabeled=Decimal("0.05"),
        missed_emis=0,
    )
    assert result.score is not None
    assert result.score >= 80
    assert result.parts["cards"] is None


def test_unknown_debit_is_not_outflow() -> None:
    flow = cashflow(
        [
            _tx("10000.00", Intent.INCOME),
            _tx("-3000.00", Intent.UNKNOWN),
            _tx("-1000.00", Intent.EXPENSE, category=Category.DINING),
        ]
    )
    assert flow.outflow == Decimal("1000.00")
    assert flow.inflow == Decimal("10000.00")


def test_build_report_month_dto() -> None:
    txs = [
        _tx("50000", Intent.INCOME, category=Category.SALARY),
        _tx("-1000", Intent.EXPENSE, category=Category.DINING, channel=Channel.UPI),
    ]
    report = build_report(
        year=2026,
        month=8,
        transactions=txs,
        accounts=[],
        months=[],
        occurrences=[],
    )
    assert report.flow.inflow == Decimal("50000")
    assert report.categories[0][0] == "dining"
    assert report.salary.count == 1
    assert report.salary.modal_day == 10


def test_missed_emi_counts_only_report_month() -> None:
    occ = [
        EmiOccurrence(
            loan_id="l1",
            due_date=datetime(2026, 7, 5, tzinfo=timezone.utc),
            expected=Decimal("1000"),
            status=EmiStatus.MISSED,
        ),
        EmiOccurrence(
            loan_id="l1",
            due_date=datetime(2026, 8, 5, tzinfo=timezone.utc),
            expected=Decimal("1000"),
            status=EmiStatus.MISSED,
        ),
    ]
    report = build_report(
        year=2026,
        month=8,
        transactions=[],
        accounts=[],
        months=[],
        occurrences=occ,
    )
    assert report.missed_emis == 1
