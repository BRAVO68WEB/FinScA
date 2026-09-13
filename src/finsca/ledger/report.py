"""Load a month of ledger data and build the report DTO."""

from __future__ import annotations

from finsca.core.models import Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import loans as loan_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.reports.monthly import MonthReport, build_report
from sqlalchemy.orm import Session


def report_for(session: Session, year: int, month: int) -> MonthReport:
    txs = [tx for tx in tx_repo.list_all(session) if _in_month(tx, year, month)]
    accounts = account_repo.list_all(session)
    months = account_repo.list_months(session, year=year, month=month)
    occurrences = []
    for loan in loan_repo.list_all(session):
        if loan.id:
            occurrences.extend(loan_repo.list_occurrences(session, loan.id))
    return build_report(
        year=year,
        month=month,
        transactions=txs,
        accounts=accounts,
        months=months,
        occurrences=occurrences,
    )


def latest_month(session: Session) -> tuple[int, int] | None:
    txs = tx_repo.list_all(session)
    if not txs:
        return None
    last = max(tx.posted_at for tx in txs)
    return last.year, last.month


def _in_month(tx: Transaction, year: int, month: int) -> bool:
    return tx.posted_at.year == year and tx.posted_at.month == month
