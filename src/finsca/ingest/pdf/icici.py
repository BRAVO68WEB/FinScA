from __future__ import annotations

import re
from decimal import Decimal

from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import batch_from, parse_header
from finsca.ingest.pdf.patterns import amounts_in, posted_at
from finsca.ingest.types import ParsedBatch, ParsedLine

_ROW = re.compile(r"^(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+(.+)$")
_SKIP = re.compile(
    r"^(statement of|transaction |s no\.|date amount|www\.icici|please call|"
    r"never share|sincerly|team icici|this is a system|legends|rchg -|\d+$)",
    re.I,
)


def parse_icici(text: str) -> ParsedBatch:
    header = parse_header(text, institution="ICICI")
    lines, warnings, opening, closing = _parse_lines(text)
    if header.opening is None:
        header.opening = opening
    if header.closing is None:
        header.closing = closing
    if header.last4 is None:
        match = re.search(r"account\s+no\.?\s*(\d{4,})", text, re.I)
        if match:
            header.last4 = match.group(1)[-4:]
            header.display_name = f"ICICI {header.last4}"
    return batch_from("icici", header, lines, warnings)


def _parse_lines(text: str) -> tuple[list[ParsedLine], list[str], Decimal | None, Decimal | None]:
    rows: list[ParsedLine] = []
    warnings: list[str] = []
    credit_next = False
    opening = closing = None
    running: Decimal | None = None
    pending_desc: list[str] = []
    for raw in text.splitlines():
        row = raw.strip()
        if not row:
            continue
        if row.lower() == "credit trxn":
            credit_next = True
            continue
        if _SKIP.match(row) or "Your Base Branch" in row or "Transaction Withdrawal" in row:
            pending_desc.clear()
            continue
        match = _ROW.match(row)
        if match is None:
            if rows and not credit_next:
                rows[-1].description = (rows[-1].description + " " + row).strip()
            else:
                pending_desc.append(row)
            continue
        amounts = amounts_in(match.group(3))
        if len(amounts) < 2:
            warnings.append(f"skipped line: {row[:80]}")
            continue
        txn, balance = amounts[0], amounts[-1]
        if running is None:
            signed = abs(txn) if credit_next else -abs(txn)
            opening = balance - signed
        else:
            signed = abs(txn) if balance > running else -abs(txn)
        desc = " ".join(part for part in pending_desc if not part.lower().startswith("your base"))
        pending_desc.clear()
        credit_next = False
        running = balance
        closing = balance
        rows.append(
            ParsedLine(
                posted_at=posted_at(match.group(2)),
                amount=signed,
                description=desc or "ICICI",
                channel=infer_channel(desc),
            )
        )
    return rows, warnings, opening, closing
