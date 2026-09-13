from __future__ import annotations

from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.generic import parse_generic
from finsca.ingest.pdf.patterns import DATE_RE, amounts_in, posted_at
from finsca.ingest.types import ParsedBatch, ParsedLine

_COLUMN_MARKERS = ("WITHDRAWAL AMT", "DEPOSIT AMT", "WITHDRAWAL", "DEPOSIT")


def parse_hdfc(text: str) -> ParsedBatch:
    batch = parse_generic(text, parser="hdfc", institution="HDFC")
    if _has_columns(text):
        column_lines = _parse_columns(text)
        if column_lines:
            batch.lines = column_lines
            batch.warnings = [w for w in batch.warnings if not w.startswith("skipped line")]
    return batch


def _has_columns(text: str) -> bool:
    upper = text.upper()
    return "WITHDRAWAL" in upper and "DEPOSIT" in upper


def _parse_columns(text: str) -> list[ParsedLine]:
    lines: list[ParsedLine] = []
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
            continue
        balance = amounts[-1]
        body = amounts[:-1]
        if len(body) >= 2:
            withdrawal, deposit = body[0], body[1]
            amount = -abs(withdrawal) if withdrawal else abs(deposit)
        else:
            amount = _signed_from_narration(body[0], rest)
        desc = _narration(rest, amounts)
        if not desc:
            continue
        lines.append(
            ParsedLine(
                posted_at=posted_at(date_s),
                amount=amount,
                description=desc,
                channel=infer_channel(desc),
            )
        )
        _ = balance
    return lines


def _signed_from_narration(amount: Decimal, rest: str) -> Decimal:
    upper = rest.upper()
    if any(token in upper for token in (" CR", "CREDIT", "SALARY", "NEFT CR", "IMPS CR")):
        return abs(amount)
    return -abs(amount)


def _narration(rest: str, amounts: list[Decimal]) -> str:
    cleaned = rest
    for value in amounts:
        token = f"{value:,.2f}"
        cleaned = cleaned.replace(token, " ")
        cleaned = cleaned.replace(str(value), " ")
    return " ".join(cleaned.split())
