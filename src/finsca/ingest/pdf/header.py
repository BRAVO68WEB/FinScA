from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from finsca.core.enums import AccountType
from finsca.ingest.pdf.patterns import (
    CLOSING_RE,
    OPENING_RE,
    first_amount,
    first_customer,
    first_last4,
    first_period,
)
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine


class StatementHeader(BaseModel):
    last4: str | None = None
    institution: str | None = None
    display_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    opening: Decimal | None = None
    closing: Decimal | None = None


def account_display_name(
    institution: str | None,
    last4: str | None,
    customer: str | None = None,
) -> str | None:
    if institution and last4:
        return f"{institution} {last4}"
    if institution:
        return institution
    if last4:
        return f"Account {last4}"
    return customer


def parse_header(text: str, *, institution: str | None = None) -> StatementHeader:
    period = first_period(text)
    last4 = first_last4(text)
    customer = first_customer(text)
    return StatementHeader(
        last4=last4,
        institution=institution,
        display_name=account_display_name(institution, last4, customer),
        period_start=period[0] if period else None,
        period_end=period[1] if period else None,
        opening=first_amount(OPENING_RE, text),
        closing=first_amount(CLOSING_RE, text),
    )


def batch_from(
    parser: str,
    header: StatementHeader,
    lines: list[ParsedLine],
    warnings: list[str],
) -> ParsedBatch:
    if not lines:
        warnings = [*warnings, "no transaction lines matched"]
    return ParsedBatch(
        parser=parser,
        account=AccountHint(
            last4=header.last4,
            institution=header.institution,
            display_name=header.display_name,
            account_type=AccountType.SAVINGS,
        ),
        period_start=header.period_start,
        period_end=header.period_end,
        opening=header.opening,
        closing=header.closing,
        lines=lines,
        warnings=warnings,
    )
