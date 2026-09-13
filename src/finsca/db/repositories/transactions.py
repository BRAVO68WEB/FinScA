from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.enums import Category, IncomeReview, Intent, LabelSource, SourceKind
from finsca.core.ids import new_id
from finsca.core.models import Transaction
from finsca.core.money import to_paise
from finsca.db import schema as tables
from finsca.db.mapping import transaction_from_row
from finsca.finance.dedupe import event_hash
from finsca.finance.normalize import normalize_description


class DuplicateTransactionError(ValueError):
    def __init__(self, existing: Transaction) -> None:
        self.existing = existing
        super().__init__(f"duplicate transaction {existing.content_hash}")


def add(session: Session, payload: Transaction) -> Transaction:
    created, is_new = add_event(session, payload)
    if not is_new:
        raise DuplicateTransactionError(created)
    return created


def add_event(session: Session, payload: Transaction) -> tuple[Transaction, bool]:
    description_norm = payload.description_norm or normalize_description(payload.description_raw)
    digest = payload.content_hash or event_hash(payload.account_id, payload.posted_at, payload.amount)
    existing = get_by_hash(session, digest)
    if existing is not None:
        enrich_source(session, existing, payload.source_kind)
        return existing, False
    row = tables.Transaction(
        id=new_id(),
        account_id=payload.account_id,
        posted_at=payload.posted_at,
        value_date=payload.value_date,
        amount_paise=to_paise(payload.amount),
        currency=payload.currency,
        description_raw=payload.description_raw,
        description_norm=description_norm,
        counterparty=payload.counterparty,
        merchant=payload.merchant,
        channel=payload.channel.value,
        category=payload.category.value if payload.category else None,
        subcategory=payload.subcategory,
        intent=payload.intent.value,
        gst_rate=payload.gst_rate,
        gst_amount_paise=to_paise(payload.gst_amount) if payload.gst_amount is not None else None,
        gst_source=payload.gst_source.value,
        source_kind=payload.source_kind.value,
        source_ref=payload.source_ref or payload.source_kind.value,
        content_hash=digest,
        ingest_run_id=payload.ingest_run_id,
        duplicate_of_id=payload.duplicate_of_id,
        self_transfer_group_id=payload.self_transfer_group_id,
        exclude_from_cashflow=payload.exclude_from_cashflow,
        label_source=payload.label_source.value if payload.label_source else None,
        label_confidence=payload.label_confidence,
        income_review=payload.income_review.value,
    )
    session.add(row)
    session.flush()
    return transaction_from_row(row), True


def get(session: Session, transaction_id: str) -> Transaction | None:
    row = session.get(tables.Transaction, transaction_id)
    return transaction_from_row(row) if row else None


def get_by_hash(session: Session, digest: str) -> Transaction | None:
    row = session.scalar(select(tables.Transaction).where(tables.Transaction.content_hash == digest))
    return transaction_from_row(row) if row else None


def enrich_source(session: Session, existing: Transaction, source_kind: SourceKind) -> Transaction:
    if existing.id is None:
        return existing
    row = session.get(tables.Transaction, existing.id)
    if row is None:
        return existing
    tag = source_kind.value
    seen = (row.source_ref or row.source_kind).split(";")
    if tag not in seen:
        row.source_ref = ";".join([*seen, tag])
        session.flush()
    return transaction_from_row(row)


def list_all(session: Session) -> list[Transaction]:
    rows = session.scalars(select(tables.Transaction).order_by(tables.Transaction.posted_at)).all()
    return [transaction_from_row(row) for row in rows]


def list_pending_review(session: Session) -> list[Transaction]:
    rows = session.scalars(
        select(tables.Transaction)
        .where(
            tables.Transaction.income_review == IncomeReview.PENDING.value,
            tables.Transaction.amount_paise > 0,
        )
        .order_by(tables.Transaction.posted_at)
    ).all()
    return [transaction_from_row(row) for row in rows]


def mark_self_transfer(session: Session, debit_id: str, credit_id: str, group_id: str) -> None:
    for tx_id in (debit_id, credit_id):
        row = session.get(tables.Transaction, tx_id)
        if row is None:
            continue
        row.intent = Intent.SELF_TRANSFER.value
        row.exclude_from_cashflow = True
        row.self_transfer_group_id = group_id
        row.income_review = IncomeReview.SKIPPED.value
    session.flush()


def apply_review(
    session: Session,
    tx_id: str,
    *,
    intent: Intent,
    income_review: IncomeReview,
    exclude_from_cashflow: bool,
    category: Category | None = None,
) -> Transaction:
    row = session.get(tables.Transaction, tx_id)
    if row is None:
        raise KeyError(tx_id)
    row.intent = intent.value
    row.income_review = income_review.value
    row.exclude_from_cashflow = exclude_from_cashflow
    if category is not None:
        row.category = category.value
        row.label_source = LabelSource.MANUAL.value
    session.flush()
    return transaction_from_row(row)


def list_for_account(session: Session, account_id: str) -> list[Transaction]:
    rows = session.scalars(
        select(tables.Transaction)
        .where(tables.Transaction.account_id == account_id)
        .order_by(tables.Transaction.posted_at)
    ).all()
    return [transaction_from_row(row) for row in rows]
