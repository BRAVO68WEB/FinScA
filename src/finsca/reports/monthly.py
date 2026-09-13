"""Monthly report DTO built from domain objects — no SQL."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from finsca.core.enums import AccountType, Channel, EmiStatus, Intent
from finsca.core.models import Account, AccountMonth, EmiOccurrence, Transaction
from finsca.finance.cashflow import Cashflow, cashflow
from finsca.finance.channels import channel_mix
from finsca.finance.gst import GstTotals, gst_totals
from finsca.finance.habits import top_categories, unlabeled_share
from finsca.finance.health import Health, health_score
from finsca.finance.salary import SalaryCycle, salary_cycle


@dataclass(frozen=True)
class MonthReport:
    year: int
    month: int
    flow: Cashflow
    categories: list[tuple[str, Decimal]]
    channels: list[tuple[Channel, Decimal]]
    salary: SalaryCycle
    gst: GstTotals
    health: Health
    emi_paid: Decimal
    missed_emis: int


def build_report(
    *,
    year: int,
    month: int,
    transactions: list[Transaction],
    accounts: list[Account],
    months: list[AccountMonth],
    occurrences: list[EmiOccurrence],
) -> MonthReport:
    flow = cashflow(transactions)
    income = sum((tx.amount for tx in transactions if tx.intent is Intent.INCOME), Decimal("0"))
    emi_paid = sum((abs(tx.amount) for tx in transactions if tx.intent is Intent.EMI), Decimal("0"))
    emi_ratio = (emi_paid / income) if income > 0 else None
    missed = sum(1 for item in occurrences if item.status is EmiStatus.MISSED)
    salary = salary_cycle(transactions)
    health = health_score(
        flow=flow,
        emi_to_income=emi_ratio,
        cc_util=_cc_util(accounts, months),
        emergency_months=_emergency_months(accounts, months, flow.outflow),
        salary_regular=salary.regular,
        unlabeled=unlabeled_share(transactions),
        missed_emis=missed,
    )
    return MonthReport(
        year=year,
        month=month,
        flow=flow,
        categories=top_categories(transactions),
        channels=channel_mix(transactions),
        salary=salary,
        gst=gst_totals(transactions),
        health=health,
        emi_paid=emi_paid,
        missed_emis=missed,
    )


def _cc_util(accounts: list[Account], months: list[AccountMonth]) -> Decimal | None:
    cards = [item for item in accounts if item.type is AccountType.CREDIT_CARD and item.credit_limit]
    if not cards:
        return None
    used = Decimal("0")
    limit = Decimal("0")
    by_account = {item.account_id: item for item in months}
    for card in cards:
        if card.id is None or card.credit_limit is None:
            continue
        limit += card.credit_limit
        month = by_account.get(card.id)
        if month:
            used += abs(month.closing)
    if limit <= 0:
        return None
    return used / limit


def _emergency_months(
    accounts: list[Account],
    months: list[AccountMonth],
    outflow: Decimal,
) -> Decimal | None:
    if outflow <= 0:
        return None
    liquid_types = {AccountType.SAVINGS, AccountType.CURRENT}
    liquid = Decimal("0")
    by_account = {item.account_id: item for item in months}
    for account in accounts:
        if account.type not in liquid_types or account.id is None:
            continue
        month = by_account.get(account.id)
        if month:
            liquid += month.closing
    return (liquid / outflow).quantize(Decimal("0.01"))
