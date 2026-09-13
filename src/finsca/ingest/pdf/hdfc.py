from __future__ import annotations

from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.generic import parse_generic_lines
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.pdf.patterns import DATE_RE, amounts_in, posted_at
from finsca.ingest.types import ParsedBatch, ParsedLine

_COLUMN_MARKERS = ("WITHDRAWAL AMT", "DEPOSIT AMT", "WITHDRAWAL", "DEPOSIT")


def parse_hdfc(text: str) -> ParsedBatch:
    header = parse_header(text, institution="HDFC")
    if _has_columns(text):
        lines, warnings = _parse_columns(text)
        if not lines:
            lines, warnings = parse_generic_lines(text)
    else:
        lines, warnings = parse_generic_lines(text)
    return batch_from("hdfc", header, lines, warnings)


def _has_columns(text: str) -> bool:
    upper = text.upper()
    return "WITHDRAWAL" in upper and "DEPOSIT" in upper


def _parse_columns(text: str) -> tuple[list[ParsedLine], list[str]]:
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    for raw in text.splitlines():
        row = raw.strip()
        dated = DATE_RE.match(row)
        if not row or dated is None:
            continue
        if any(marker in row.upper() for marker in _COLUMN_MARKERS):
            continue
        date_s = dated.group(1)
        rest = row[len(date_s) :].strip()
        amounts = amounts_in(rest)
        if len(amounts) < 2:
            warnings.append(f"skipped line: {row[:80]}")
            continue
        body = amounts[:-1]
        if len(body) >= 2:
            withdrawal, deposit = body[0], body[1]
            amount = -abs(withdrawal) if withdrawal else abs(deposit)
        else:
            amount = _signed_from_narration(body[0], rest)
        desc = _narration(rest, amounts)
        if not desc:
            warnings.append(f"skipped line: {row[:80]}")
            continue
        lines.append(
            ParsedLine(
                posted_at=posted_at(date_s),
                amount=amount,
                description=desc,
                channel=infer_channel(desc),
            )
        )
    return lines, warnings


def _signed_from_narration(amount: Decimal, rest: str) -> Decimal:
    upper = rest.upper()
    if any(token in upper for token in (" CR", "CREDIT", "SALARY", "NEFT CR", "IMPS CR")):
        return abs(amount)
    return -abs(amount)


def _narration(rest: str, amounts: list[Decimal]) -> str:
    cleaned = rest
    for value in amounts:
        cleaned = cleaned.replace(f"{value:,.2f}", " ")
        cleaned = cleaned.replace(str(value), " ")
    return " ".join(cleaned.split())
