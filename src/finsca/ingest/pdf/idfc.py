from __future__ import annotations

import re
from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.pdf.patterns import amounts_in, posted_at, strip_amounts
from finsca.ingest.types import ParsedBatch, ParsedLine

_DATED = re.compile(
    r"^(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}-[A-Za-z]{3}-\d{4})\s+(.*)$"
)
_SKIP = re.compile(
    r"^(statement of|customer |account |statement period|communication|"
    r"registered office|page \d+|transaction cheque|value date|date no|"
    r"opening balance total|branch address|nomination|nominee|email id|phone no)",
    re.I,
)


def parse_idfc(text: str) -> ParsedBatch:
    header = parse_header(text, institution="IDFC")
    _apply_summary(text, header)
    if header.last4 is None:
        match = re.search(r"account\s+no\s*[:\-]?\s*(\d{4,})", text, re.I)
        if match:
            header.last4 = match.group(1)[-4:]
            header.display_name = f"IDFC {header.last4}"
    lines, warnings = _parse_lines(text, running=header.opening)
    return batch_from("idfc", header, lines, warnings)


def _apply_summary(text: str, header) -> None:
    block = re.search(
        r"Opening Balance Total Debit Total Credit Closing Balance\s+"
        r"((?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})\s+"
        r"(?:(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})\s+"
        r"(?:(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})\s+"
        r"((?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})",
        text,
        re.I,
    )
    if block:
        from finsca.ingest.pdf.patterns import parse_amount

        header.opening = parse_amount(block.group(1))
        header.closing = parse_amount(block.group(2))


_NARR_START = re.compile(r"^(UPI/|POS|NEFT|IMPS|RTGS|ACH|NACH|INT|MONTHLY|I/?FT)", re.I)


def _parse_lines(text: str, running: Decimal | None) -> tuple[list[ParsedLine], list[str]]:
    pending: list[str] = []
    rows: list[ParsedLine] = []
    warnings: list[str] = []
    for raw in text.splitlines():
        row = raw.strip()
        if not row or _SKIP.match(row):
            continue
        match = _DATED.match(row)
        if match is None:
            if _NARR_START.match(row):
                pending.append(row)
            continue
        rest = match.group(3)
        amounts = amounts_in(rest)
        if len(amounts) < 2:
            if _NARR_START.match(row):
                pending.append(row)
            continue
        txn, balance = amounts[0], amounts[-1]
        blob = " ".join([*pending, rest])
        pending.clear()
        if running is None:
            signed = _signed(blob, txn)
        else:
            signed = abs(txn) if balance > running else -abs(txn)
        running = balance
        desc = strip_amounts(blob)
        rows.append(
            ParsedLine(
                posted_at=posted_at(match.group(1)),
                amount=signed,
                description=desc or "IDFC",
                channel=infer_channel(desc),
            )
        )
    return rows, warnings


def _signed(blob: str, amount: Decimal) -> Decimal:
    upper = blob.upper()
    if "/CR/" in upper:
        return abs(amount)
    return -abs(amount)
