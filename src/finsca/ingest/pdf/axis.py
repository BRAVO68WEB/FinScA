from __future__ import annotations

import re
from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.pdf.patterns import amounts_in, posted_at
from finsca.ingest.types import ParsedBatch, ParsedLine

_SKIP = re.compile(
    r"^(tran date|opening balance|closing balance|transaction total|legends|"
    r"unless |we would|registered office|branch address|this is a system|"
    r"\+\+\+\+|iconn-|with effect|deposit insurance|in compliance|to ensure)",
    re.I,
)
_DATED = re.compile(r"^(\d{2}-\d{2}-\d{4})\b")


def parse_axis(text: str) -> ParsedBatch:
    header = parse_header(text, institution="AXIS")
    lines, warnings, opening, closing = _parse_lines(text)
    if header.opening is None:
        header.opening = opening
    if header.closing is None:
        header.closing = closing
    return batch_from("axis", header, lines, warnings)


def _parse_lines(text: str) -> tuple[list[ParsedLine], list[str], Decimal | None, Decimal | None]:
    pending: list[str] = []
    rows: list[ParsedLine] = []
    warnings: list[str] = []
    running: Decimal | None = None
    opening = closing = None
    for raw in text.splitlines():
        row = raw.strip()
        if not row:
            continue
        if row.upper().startswith("OPENING BALANCE"):
            found = amounts_in(row)
            opening = found[0] if found else opening
            running = opening
            pending.clear()
            continue
        if row.upper().startswith("CLOSING BALANCE"):
            found = amounts_in(row)
            closing = found[0] if found else closing
            pending.clear()
            continue
        if _SKIP.match(row):
            continue
        dated = _DATED.match(row)
        if dated is None:
            if not row.startswith("http") and "REGISTERED" not in row.upper():
                pending.append(row)
            continue
        date_s = dated.group(1)
        rest = row[len(date_s) :].strip()
        amounts = amounts_in(rest)
        if len(amounts) < 2:
            pending.append(row)
            continue
        balance = amounts[-1]
        txn = amounts[0]
        signed = -abs(txn) if running is not None and balance < running else abs(txn)
        if running is not None and balance == running:
            signed = Decimal("0.00")
        desc = " ".join([*pending, _narration(rest, amounts)])
        pending.clear()
        running = balance
        rows.append(
            ParsedLine(
                posted_at=posted_at(date_s),
                amount=signed,
                description=desc or "AXIS",
                channel=infer_channel(desc),
            )
        )
    return rows, warnings, opening, closing


def _narration(rest: str, amounts: list[Decimal]) -> str:
    cleaned = rest
    for value in amounts:
        cleaned = cleaned.replace(f"{value:.2f}", " ")
        cleaned = cleaned.replace(f"{value:,.2f}", " ")
    cleaned = re.sub(r"\b\d{3,4}\s*$", "", cleaned)
    return " ".join(cleaned.split())
