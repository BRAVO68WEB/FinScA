"""Shared run context and the pydantic payloads agents accept."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from finsca.config.settings import Settings
from finsca.core.enums import SourceKind
from finsca.core.models import Transaction
from finsca.ingest.types import IngestFileResult, ParsedBatch
from finsca.reports.monthly import MonthReport


@dataclass
class IngestRunCtx:
    settings: Settings
    session: Session
    run_id: str | None = None


@dataclass
class AskCtx:
    settings: Settings
    session: Session
    question: str = ""


class ParseInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path
    kind: SourceKind


class ParseOutput(BaseModel):
    batch: ParsedBatch


class PersistInput(BaseModel):
    batch: ParsedBatch
    run_id: str


class PersistOutput(BaseModel):
    inserted: int
    dupes: int
    pending_review: int


class NormalizeInput(BaseModel):
    inserted: int
    dupes: int


class NormalizeOutput(BaseModel):
    inserted: int
    dupes: int


class StageInput(BaseModel):
    """Stages that only need the session on the context."""


class CountOutput(BaseModel):
    count: int


class LabelOutput(BaseModel):
    rules: int = 0
    yaml: int = 0
    compact: int = 0


class ArchiveInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    files: list[IngestFileResult]
    dest: Path
    run_id: str


class ArchiveOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    files: list[IngestFileResult]


class ReportInput(BaseModel):
    year: int
    month: int


class ReportOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    report: MonthReport


class CashflowInput(BaseModel):
    transactions: list[Transaction] = []


class CashflowOutput(BaseModel):
    inflow: Decimal
    outflow: Decimal
    net: Decimal
    savings_rate: Decimal | None


class HealthInput(BaseModel):
    inflow: Decimal = Decimal("0")
    outflow: Decimal = Decimal("0")
    savings_rate: Decimal | None = None
    emi_to_income: Decimal | None = None
    cc_util: Decimal | None = None
    emergency_months: Decimal | None = None
    salary_regular: bool | None = None
    unlabeled: Decimal | None = None
    missed_emis: int = 0


class HealthOutput(BaseModel):
    score: int | None
    parts: dict[str, int | None]
