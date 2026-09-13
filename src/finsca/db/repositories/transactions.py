from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.ids import content_hash, new_id
from finsca.core.models import Transaction
from finsca.core.money import to_paise
from finsca.db import schema as tables
from finsca.db.mapping import transaction_from_row
from finsca.finance.normalize import normalize_description


class DuplicateTransactionError(ValueError):
    def __init__(self, existing: Transaction) -> None:
        self.existing = existing
        super().__init__(f"duplicate transaction {existing.content_hash}")


def hash_for(tx: Transaction, description_norm: str) -> str:
    return content_hash(
        tx.account_id,
        tx.posted_at.date().isoformat(),
        str(to_paise(tx.amount)),
        description_norm[:48],
        tx.source_kind.value,
    )


def add(session: Session, payload: Transaction) -> Transaction:
    description_norm = payload.description_norm or normalize_description(payload.description_raw)
    digest = payload.content_hash or hash_for(payload, description_norm)
    existing = get_by_hash(session, digest)
    if existing is not None:
        raise DuplicateTransactionError(existing)
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
        source_ref=payload.source_ref,
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
    return transaction_from_row(row)


def get(session: Session, transaction_id: str) -> Transaction | None:
    row = session.get(tables.Transaction, transaction_id)
    return transaction_from_row(row) if row else None


def get_by_hash(session: Session, digest: str) -> Transaction | None:
    row = session.scalar(select(tables.Transaction).where(tables.Transaction.content_hash == digest))
    return transaction_from_row(row) if row else None


def list_for_account(session: Session, account_id: str) -> list[Transaction]:
    rows = session.scalars(
        select(tables.Transaction)
        .where(tables.Transaction.account_id == account_id)
        .order_by(tables.Transaction.posted_at)
    ).all()
    return [transaction_from_row(row) for row in rows]
