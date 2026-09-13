from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.enums import EmiStatus, LoanStatus
from finsca.core.ids import new_id
from finsca.core.models import EmiOccurrence, Loan
from finsca.core.money import to_paise
from finsca.db import schema as tables
from finsca.db.mapping import loan_from_row, occurrence_from_row


def add(session: Session, loan: Loan) -> Loan:
    row = tables.Loan(
        id=new_id(),
        name=loan.name,
        lender=loan.lender,
        principal_paise=to_paise(loan.principal),
        emi_paise=to_paise(loan.emi),
        emi_day=loan.emi_day,
        tenure_months=loan.tenure_months,
        rate_bps=loan.rate_bps,
        start_date=loan.start_date,
        status=loan.status.value,
        account_id=loan.account_id,
    )
    session.add(row)
    session.flush()
    return loan_from_row(row)


def get(session: Session, loan_id: str) -> Loan | None:
    row = session.get(tables.Loan, loan_id)
    return loan_from_row(row) if row else None


def resolve(session: Session, token: str) -> Loan | None:
    needle = token.strip()
    exact = session.get(tables.Loan, needle)
    if exact:
        return loan_from_row(exact)
    hits = [
        row
        for row in session.scalars(select(tables.Loan)).all()
        if row.id.startswith(needle) or row.name.casefold() == needle.casefold()
    ]
    if len(hits) == 1:
        return loan_from_row(hits[0])
    return None


def list_all(session: Session, *, active_only: bool = False) -> list[Loan]:
    stmt = select(tables.Loan).order_by(tables.Loan.name)
    if active_only:
        stmt = stmt.where(tables.Loan.status == LoanStatus.ACTIVE.value)
    return [loan_from_row(row) for row in session.scalars(stmt).all()]


def close(session: Session, loan_id: str) -> Loan:
    row = session.get(tables.Loan, loan_id)
    if row is None:
        raise KeyError(loan_id)
    row.status = LoanStatus.CLOSED.value
    session.flush()
    return loan_from_row(row)


def list_occurrences(session: Session, loan_id: str) -> list[EmiOccurrence]:
    rows = session.scalars(
        select(tables.EmiOccurrence)
        .where(tables.EmiOccurrence.loan_id == loan_id)
        .order_by(tables.EmiOccurrence.due_date)
    ).all()
    return [occurrence_from_row(row) for row in rows]


def upsert_occurrence(session: Session, item: EmiOccurrence) -> EmiOccurrence:
    existing = session.scalar(
        select(tables.EmiOccurrence).where(
            tables.EmiOccurrence.loan_id == item.loan_id,
            tables.EmiOccurrence.due_date == item.due_date,
        )
    )
    if existing is None:
        row = tables.EmiOccurrence(
            id=new_id(),
            loan_id=item.loan_id,
            due_date=item.due_date,
            expected_paise=to_paise(item.expected),
            status=item.status.value,
            transaction_id=item.transaction_id,
        )
        session.add(row)
        session.flush()
        return occurrence_from_row(row)
    existing.status = item.status.value
    existing.transaction_id = item.transaction_id
    existing.expected_paise = to_paise(item.expected)
    session.flush()
    return occurrence_from_row(existing)
