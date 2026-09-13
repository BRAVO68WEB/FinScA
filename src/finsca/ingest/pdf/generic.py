from __future__ import annotations

from decimal import Decimal

from finsca.core.enums import AccountType
from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.patterns import (
    CLOSING_RE,
    DATE_RE,
    LINE_RE,
    OPENING_RE,
    first_amount,
    first_customer,
    first_last4,
    first_period,
    parse_amount,
    posted_at,
)
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine


def parse_generic(text: str, *, parser: str = "generic", institution: str | None = None) -> ParsedBatch:
    period = first_period(text)
    last4 = first_last4(text)
    customer = first_customer(text)
    opening = first_amount(OPENING_RE, text)
    closing = first_amount(CLOSING_RE, text)
    hint = AccountHint(
        last4=last4,
        institution=institution,
        display_name=_display_name(institution, last4, customer),
        account_type=AccountType.SAVINGS,
    )
    lines, warnings = _parse_lines(text)
    if not lines:
        warnings.append("no transaction lines matched")
    return ParsedBatch(
        parser=parser,
        account=hint,
        period_start=period[0] if period else None,
        period_end=period[1] if period else None,
        opening=opening,
        closing=closing,
        lines=lines,
        warnings=warnings,
    )


def _display_name(institution: str | None, last4: str | None, customer: str | None) -> str | None:
    if institution and last4:
        return f"{institution} {last4}"
    if institution:
        return institution
    if last4:
        return f"Account {last4}"
    return customer


def _parse_lines(text: str) -> tuple[list[ParsedLine], list[str]]:
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    running: Decimal | None = None
    for raw in text.splitlines():
        row = raw.strip()
        if not row or not DATE_RE.match(row):
            continue
        match = LINE_RE.match(row)
        if not match:
            warnings.append(f"skipped line: {row[:80]}")
            continue
        date_s, desc, first, second, suffix = match.groups()
        amount = parse_amount(first)
        signed = _sign(amount, suffix, parse_amount(second) if second else None, running)
        if second:
            running = parse_amount(second)
        lines.append(
            ParsedLine(
                posted_at=posted_at(date_s),
                amount=signed,
                description=" ".join(desc.split()),
                channel=infer_channel(desc),
            )
        )
    return lines, warnings


def _sign(
    amount: Decimal,
    suffix: str | None,
    balance: Decimal | None,
    previous_balance: Decimal | None,
) -> Decimal:
    if suffix:
        return -abs(amount) if suffix.lower() == "dr" else abs(amount)
    if balance is not None and previous_balance is not None:
        return -abs(amount) if balance < previous_balance else abs(amount)
    if suffix is None and balance is None:
        return -abs(amount)
    return -abs(amount)
