from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field

from finsca.core.enums import AccountType, Channel, IngestStatus, SourceKind


class AccountHint(BaseModel):
    last4: str | None = None
    institution: str | None = None
    display_name: str | None = None
    account_type: AccountType = AccountType.SAVINGS


class ParsedLine(BaseModel):
    posted_at: datetime
    amount: Decimal
    description: str
    channel: Channel = Channel.OTHER
    last4: str | None = None
    institution: str | None = None


class ParsedBatch(BaseModel):
    parser: str
    source_kind: SourceKind = SourceKind.PDF
    account: AccountHint = Field(default_factory=AccountHint)
    period_start: date | None = None
    period_end: date | None = None
    opening: Decimal | None = None
    closing: Decimal | None = None
    lines: list[ParsedLine] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IngestFileResult(BaseModel):
    path: Path
    sha256: str
    parser: str | None = None
    tx_count: int = 0
    dupe_count: int = 0
    pending_review: int = 0
    warning: str | None = None
    error: str | None = None
    archived_as: str | None = None
    kind: SourceKind | None = None
    relpath: str | None = None


class IngestSummary(BaseModel):
    run_id: str | None = None
    status: IngestStatus = IngestStatus.SUCCESS
    parsed_count: int = 0
    dupe_count: int = 0
    pending_review_count: int = 0
    archive_path: Path | None = None
    files: list[IngestFileResult] = Field(default_factory=list)
    empty: bool = False

    @property
    def succeeded(self) -> list[IngestFileResult]:
        return [item for item in self.files if item.error is None]

    @property
    def failed(self) -> list[IngestFileResult]:
        return [item for item in self.files if item.error is not None]
