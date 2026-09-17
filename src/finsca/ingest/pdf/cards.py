"""Credit-card statement lines: date + narration + amount + optional Dr/Cr."""

from __future__ import annotations

import re
from decimal import Decimal

from finsca.core.enums import AccountType, Channel
from finsca.finance.channels import infer_channel
from finsca.ingest.pdf.header import account_display_name, parse_header
from finsca.ingest.pdf.patterns import card_last4, parse_amount, posted_at
from finsca.ingest.types import AccountHint, ParsedBatch, ParsedLine

_AMOUNT = r"((?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})"
_DATE = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})"
_ROW = re.compile(
    rf"^{_DATE}(?:\s*[|]\s*\d{{1,2}}:\d{{2}}|\s+\d{{1,2}}:\d{{2}})?\s+"
    rf"(.+?)\s+{_AMOUNT}\s*(Dr|Cr|DR|CR|D|C)?\s*$"
)
_HDFC_ROW = re.compile(
    rf"^(\d{{2}}/\d{{2}}/\d{{4}})\|\s*\d{{2}}:\d{{2}}\s+(.+?)\s+C\s+{_AMOUNT}\b"
)
_SKIP = re.compile(
    r"(credit limit|minimum amount|finance charge on|interest on rs|"
    r"total amount due|statement period|payment due|available credit|"
    r"billed amount|gstin|page \d+ of|total payment due)",
    re.I,
)
_CREDIT = re.compile(r"\b(payment received|payments? received|refund|reversal)\b", re.I)


def parse_card(text: str, *, bank_id: str | None = None, filename: str = "") -> ParsedBatch:
    institution = (bank_id or _institution(text) or "").upper() or None
    header = parse_header(text, institution=institution)
    card = _preferred_last4(filename, text) or header.last4
    if card:
        header.last4 = card
        header.display_name = account_display_name(institution, header.last4)
    lines, warnings = _parse_lines(text)
    return ParsedBatch(
        parser=f"{(bank_id or 'card')}_card",
        account=AccountHint(
            last4=header.last4,
            institution=institution,
            display_name=header.display_name,
            account_type=AccountType.CREDIT_CARD,
        ),
        period_start=header.period_start,
        period_end=header.period_end,
        opening=header.opening,
        closing=header.closing,
        lines=lines,
        warnings=warnings,
    )


def last4_from_name(name: str) -> str | None:
    masked = _masked_last4(name)
    if masked:
        return masked
    runs = [run for run in re.findall(r"\d{4,}", name) if len(run) >= 12]
    return runs[-1][-4:] if runs else None


def _masked_last4(text: str) -> str | None:
    match = re.search(r"(\d{4})X+(\d{4})", text, re.I)
    return match.group(2) if match else None


def _preferred_last4(filename: str, text: str) -> str | None:
    return _masked_last4(filename) or card_last4(text) or last4_from_name(filename)


def _parse_lines(text: str) -> tuple[list[ParsedLine], list[str]]:
    rows: list[ParsedLine] = []
    warnings: list[str] = []
    for raw in text.splitlines():
        row = raw.strip()
        if not row or _SKIP.search(row):
            continue
        hdfc = _HDFC_ROW.match(row)
        if hdfc:
            rows.append(_line(hdfc.group(1), hdfc.group(2), hdfc.group(3), None))
            continue
        match = _ROW.match(row)
        if match is None:
            continue
        date_s, desc, amount_s, side = match.groups()
        try:
            rows.append(_line(date_s, desc, amount_s, side))
        except ValueError:
            warnings.append(f"skipped line: {row[:80]}")
    return rows, warnings


def _line(date_s: str, desc: str, amount_s: str, side: str | None) -> ParsedLine:
    cleaned = " ".join(desc.split())
    channel = infer_channel(cleaned)
    if channel is Channel.OTHER:
        channel = Channel.CREDIT_CARD
    return ParsedLine(
        posted_at=posted_at(date_s),
        amount=_signed(cleaned, parse_amount(amount_s), side),
        description=cleaned,
        channel=channel,
    )


def _signed(desc: str, amount: Decimal, side: str | None) -> Decimal:
    token = (side or "").lower()
    if token in {"cr", "c"}:
        return abs(amount)
    if token in {"dr", "d"}:
        return -abs(amount)
    if _CREDIT.search(desc):
        return abs(amount)
    return -abs(amount)


def _institution(text: str) -> str | None:
    upper = text.upper()
    for marker, name in (
        ("HDFC BANK", "HDFC"),
        ("SBI CARD", "SBI"),
        ("YES BANK", "YES"),
        ("AXIS BANK", "AXIS"),
        ("ICICI", "ICICI"),
        ("BOBCARD", "BOB"),
        ("IDFC FIRST", "IDFC"),
    ):
        if marker in upper:
            return name
    return None
