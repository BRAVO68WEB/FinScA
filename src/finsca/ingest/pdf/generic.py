from __future__ import annotations

from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.pdf.patterns import DATE_RE, LINE_RE, parse_amount, posted_at
from finsca.ingest.types import ParsedBatch, ParsedLine


def parse_generic(text: str, *, parser: str = "generic", institution: str | None = None) -> ParsedBatch:
    header = parse_header(text, institution=institution)
    lines, warnings = parse_generic_lines(text)
    return batch_from(parser, header, lines, warnings)


def parse_generic_lines(text: str) -> tuple[list[ParsedLine], list[str]]:
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
        balance = parse_amount(second) if second else None
        signed = _sign(amount, suffix, balance, running)
        if balance is not None:
            running = balance
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
    return -abs(amount)
