from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from finsca.core.enums import (
    AccountType,
    Category,
    Channel,
    GstSource,
    IncomeReview,
    Intent,
    LabelSource,
    MonthSource,
    SourceKind,
)

_LAST4 = re.compile(r"^\d{4}$")


class NewAccount(BaseModel):
    display_name: str
    type: AccountType
    institution: str | None = None
    last4: str | None = None
    upi_vpas: list[str] = Field(default_factory=list)
    holder_aliases: list[str] = Field(default_factory=list)
    currency: str = "INR"
    is_own: bool = True
    credit_limit: Decimal | None = None

    @field_validator("last4")
    @classmethod
    def last4_is_digits(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if not _LAST4.fullmatch(value):
            raise ValueError("last4 must be 4 digits")
        return value

    @field_validator("display_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("display_name is required")
        return name


class Account(NewAccount):
    id: str
    created_at: datetime
    updated_at: datetime


class NewAccountMonth(BaseModel):
    account_id: str
    year: int
    month: int = Field(ge=1, le=12)
    opening: Decimal
    closing: Decimal
    source: MonthSource
    statement_id: str | None = None


class AccountMonth(NewAccountMonth):
    id: str


class NewTransaction(BaseModel):
    account_id: str
    posted_at: datetime
    amount: Decimal
    description_raw: str
    source_kind: SourceKind
    value_date: datetime | None = None
    currency: str = "INR"
    description_norm: str = ""
    counterparty: str | None = None
    merchant: str | None = None
    channel: Channel = Channel.OTHER
    category: Category | None = None
    subcategory: str | None = None
    intent: Intent = Intent.UNKNOWN
    gst_rate: float | None = None
    gst_amount: Decimal | None = None
    gst_source: GstSource = GstSource.NONE
    source_ref: str | None = None
    ingest_run_id: str | None = None
    duplicate_of_id: str | None = None
    self_transfer_group_id: str | None = None
    exclude_from_cashflow: bool = False
    label_source: LabelSource | None = None
    label_confidence: float | None = None
    income_review: IncomeReview = IncomeReview.PENDING


class Transaction(NewTransaction):
    id: str
    content_hash: str
