from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from finsca.core.clock import utcnow


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128))
    institution: Mapped[str | None] = mapped_column(String(128), nullable=True)
    type: Mapped[str] = mapped_column(String(32))
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    upi_vpas: Mapped[list[str]] = mapped_column(JSON, default=list)
    holder_aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    is_own: Mapped[bool] = mapped_column(Boolean, default=True)
    credit_limit_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountMonth(Base):
    __tablename__ = "account_months"
    __table_args__ = (UniqueConstraint("account_id", "year", "month", name="uq_account_month"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    opening_paise: Mapped[int] = mapped_column(Integer)
    closing_paise: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16))
    statement_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_transaction_hash"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    posted_at: Mapped[datetime] = mapped_column(DateTime)
    value_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    description_raw: Mapped[str] = mapped_column(Text)
    description_norm: Mapped[str] = mapped_column(Text, default="")
    counterparty: Mapped[str | None] = mapped_column(String(256), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(256), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), default="other")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent: Mapped[str] = mapped_column(String(32), default="unknown")
    gst_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    gst_amount_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gst_source: Mapped[str] = mapped_column(String(16), default="none")
    source_kind: Mapped[str] = mapped_column(String(16))
    source_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    ingest_run_id: Mapped[str | None] = mapped_column(ForeignKey("ingest_runs.id"), nullable=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    self_transfer_group_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exclude_from_cashflow: Mapped[bool] = mapped_column(Boolean, default=False)
    label_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    label_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    income_review: Mapped[str] = mapped_column(String(16), default="pending")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    lender: Mapped[str] = mapped_column(String(128))
    principal_paise: Mapped[int] = mapped_column(Integer)
    rate_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenure_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emi_paise: Mapped[int] = mapped_column(Integer)
    emi_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)


class EmiOccurrence(Base):
    __tablename__ = "emi_occurrences"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    due_date: Mapped[datetime] = mapped_column(DateTime)
    expected_paise: Mapped[int] = mapped_column(Integer)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="due")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    match_field: Mapped[str] = mapped_column(String(32))
    match_value: Mapped[str] = mapped_column(String(256))
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    archive_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parsed_count: Mapped[int] = mapped_column(Integer, default=0)
    dupe_count: Mapped[int] = mapped_column(Integer, default=0)
    self_transfer_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_review_count: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class IngestFile(Base):
    __tablename__ = "ingest_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ingest_run_id: Mapped[str] = mapped_column(ForeignKey("ingest_runs.id"))
    original_name: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    parser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tx_count: Mapped[int] = mapped_column(Integer, default=0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_as: Mapped[str | None] = mapped_column(String(512), nullable=True)
