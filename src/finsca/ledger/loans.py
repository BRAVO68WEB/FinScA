"""Create loans and match EMI debits to monthly occurrences."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from finsca.core.clock import utcnow
from finsca.core.enums import Category, EmiStatus, Intent, LabelSource, LoanStatus
from finsca.core.models import EmiOccurrence, Loan, Transaction
from finsca.db.repositories import loans as loan_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.finance.emi import as_due_datetime, due_on, is_candidate, months_between


def add_loan(session: Session, loan: Loan) -> Loan:
    created = loan_repo.add(session, loan)
    match_loan(session, created)
    return created


def match_all(session: Session, *, today: date | None = None) -> int:
    paid = 0
    for loan in loan_repo.list_all(session, active_only=True):
        paid += match_loan(session, loan, today=today)
    return paid


def match_loan(session: Session, loan: Loan, *, today: date | None = None) -> int:
    if loan.id is None or loan.status is not LoanStatus.ACTIVE:
        return 0
    today = today or utcnow().date()
    start = (loan.start_date.date() if loan.start_date else date(today.year, today.month, 1))
    if start > today:
        start = today
    existing = {(item.due_date.year, item.due_date.month): item for item in loan_repo.list_occurrences(session, loan.id)}
    used: set[str] = {item.transaction_id for item in existing.values() if item.transaction_id}
    candidates = [
        tx
        for tx in tx_repo.list_all(session)
        if tx.id and tx.id not in used and is_candidate(tx, loan)
    ]
    paid = 0
    for month in months_between(start, today):
        prior = existing.get((month.year, month.month))
        if prior and prior.status is EmiStatus.PAID:
            continue
        due = due_on(month.year, month.month, loan.emi_day)
        due_dt = as_due_datetime(due)
        hit = _pick(candidates, due, used)
        if hit and hit.id:
            used.add(hit.id)
            _mark_paid(session, hit)
            loan_repo.upsert_occurrence(
                session,
                EmiOccurrence(
                    loan_id=loan.id,
                    due_date=due_dt,
                    expected=loan.emi,
                    status=EmiStatus.PAID,
                    transaction_id=hit.id,
                ),
            )
            paid += 1
        else:
            status = EmiStatus.MISSED if due < today else EmiStatus.DUE
            loan_repo.upsert_occurrence(
                session,
                EmiOccurrence(
                    loan_id=loan.id,
                    due_date=due_dt,
                    expected=loan.emi,
                    status=status,
                ),
            )
    return paid


def _pick(
    candidates: list[Transaction],
    due: date,
    used: set[str],
) -> Transaction | None:
    month_hits = [
        tx
        for tx in candidates
        if tx.id not in used and tx.posted_at.year == due.year and tx.posted_at.month == due.month
    ]
    if not month_hits:
        return None
    return min(month_hits, key=lambda tx: abs(tx.posted_at.day - due.day))


def _mark_paid(session: Session, tx: Transaction) -> None:
    if tx.id is None:
        return
    tx_repo.set_label(
        session,
        tx.id,
        Category.EMI,
        source=LabelSource.TAXONOMY,
        intent=Intent.EMI,
    )
