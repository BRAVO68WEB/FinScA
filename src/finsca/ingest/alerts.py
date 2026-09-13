from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from finsca.core.enums import Channel, SourceKind
from finsca.core.money import parse_inr
from finsca.finance.channels import infer_channel
from finsca.ingest.errors import ParseError
from finsca.ingest.pdf.patterns import parse_indian_date
from finsca.ingest.types import ParsedBatch, ParsedLine

_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_AMOUNT_RE = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+\.\d{2}|\d+)", re.I)
_LAST4_RE = re.compile(
    r"(?:a/?c|acct|account|card)\s*(?:no\.?)?\s*(?:XX|X{2,})?(\d{4})",
    re.I,
)
_DATE_RE = re.compile(
    rf"(\d{{1,2}}[-/]\d{{1,2}}[-/]\d{{2,4}}|\d{{1,2}}[-/](?:{_MONTHS})[-/]\d{{2,4}})",
    re.I,
)
_PAYEE_RE = re.compile(
    r"(?:to|at|for|via|upi[:/\s]+)\s*([A-Za-z0-9@._-][A-Za-z0-9@._\s-]{1,40})",
    re.I,
)
_DEBIT_RE = re.compile(r"\b(debited|spent|paid|withdrawn|dr)\b", re.I)
_CREDIT_RE = re.compile(r"\b(credited|received|deposited|cr)\b", re.I)
_INSTITUTION = (
    ("HDFC", "HDFC"),
    ("ICICI", "ICICI"),
    ("SBI", "SBI"),
    ("AXIS", "AXIS"),
    ("KOTAK", "KOTAK"),
)


@dataclass(frozen=True)
class AlertRecord:
    body: str
    address: str = ""
    sent_at: datetime | None = None


def alerts_to_batch(records: list[AlertRecord], kind: SourceKind, parser: str) -> ParsedBatch:
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    for record in records:
        hit = parse_alert(record.body, sent_at=record.sent_at, address=record.address)
        if hit is None:
            warnings.append(f"unparsed {parser}: {record.body[:80]}")
            continue
        lines.append(hit)
    if not lines:
        raise ParseError(f"no {parser} alerts parsed")
    return ParsedBatch(parser=parser, source_kind=kind, lines=lines, warnings=warnings)


def parse_alert(
    body: str,
    *,
    sent_at: datetime | None = None,
    address: str = "",
) -> ParsedLine | None:
    amount = _amount(body)
    last4 = _last4(body)
    if amount is None or last4 is None:
        return None
    day = _date(body) or sent_at
    if day is None:
        return None
    payee = _payee(body)
    desc = payee or " ".join(body.split())[:80]
    channel = infer_channel(body)
    if channel == Channel.OTHER:
        channel = infer_channel(desc)
    return ParsedLine(
        posted_at=day,
        amount=_signed(body, amount),
        description=desc,
        channel=channel,
        last4=last4,
        institution=_institution(address, body),
    )


def _amount(body: str) -> Decimal | None:
    match = _AMOUNT_RE.search(body)
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    if "." not in raw:
        raw = f"{raw}.00"
    return parse_inr(raw)


def _last4(body: str) -> str | None:
    match = _LAST4_RE.search(body)
    return match.group(1) if match else None


def _date(body: str) -> datetime | None:
    match = _DATE_RE.search(body)
    if not match:
        return None
    raw = match.group(1)
    if re.search(_MONTHS, raw, re.I):
        for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d/%b/%y", "%d/%b/%Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
    value = parse_indian_date(raw)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _signed(body: str, amount: Decimal) -> Decimal:
    debit = bool(_DEBIT_RE.search(body))
    credit = bool(_CREDIT_RE.search(body))
    if credit and not debit:
        return abs(amount)
    if debit:
        return -abs(amount)
    if credit:
        return abs(amount)
    return -abs(amount)


def _payee(body: str) -> str | None:
    match = _PAYEE_RE.search(body)
    if not match:
        return None
    return " ".join(match.group(1).split()).strip(" .;,-")


def _institution(address: str, body: str) -> str | None:
    blob = f"{address} {body}".upper()
    for marker, name in _INSTITUTION:
        if marker in blob:
            return name
    return None
