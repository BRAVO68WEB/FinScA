from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal

from finsca.core.money import parse_inr

AMOUNT = r"(?:Rs\.?[ \t]*)?((?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})"
DATE = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"

OPENING_RE = re.compile(rf"opening\s+balance[ \t]*[:\-]?[ \t]*{AMOUNT}", re.I)
CLOSING_RE = re.compile(rf"closing\s+balance[ \t]*[:\-]?[ \t]*{AMOUNT}", re.I)
LAST4_RE = re.compile(r"(?:a/?c|account)\s*(?:no\.?|number)?\s*[:\-]?\s*[Xx\d]*(\d{4})", re.I)
PERIOD_RE = re.compile(
    rf"(?:statement\s+(?:period|from)|period|from)\s*[:\-]?\s*{DATE}\s*(?:to|-)\s*[:\-]?\s*{DATE}",
    re.I,
)
PERIOD_YMD_RE = re.compile(
    r"(?:statement\s+period|period)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})\s*(?:to|-)\s*(\d{4}-\d{2}-\d{2})",
    re.I,
)
PERIOD_LONG_RE = re.compile(
    r"period\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
    re.I,
)
CUSTOMER_RE = re.compile(r"customer\s+name\s*[:\-]?\s*(.+)", re.I)
AMOUNT_RE = re.compile(AMOUNT)
DATE_RE = re.compile(rf"^{DATE}")
LINE_RE = re.compile(
    rf"^{DATE}\s+(.+?)\s+{AMOUNT}(?:\s+{AMOUNT})?\s*(Dr|Cr|DR|CR)?\s*$"
)


def parse_amount(raw: str) -> Decimal:
    return parse_inr(raw.replace(",", ""))


def parse_indian_date(raw: str) -> date:
    text = raw.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year, month, day = (int(part) for part in text.split("-"))
        return date(year, month, day)
    if re.search(r"[A-Za-z]{3}", text):
        for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    parts = re.split(r"[-/.]", text)
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if year < 100:
        year += 2000
    return date(year, month, day)


def posted_at(raw: str) -> datetime:
    value = parse_indian_date(raw)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def first_amount(pattern: re.Pattern[str], text: str) -> Decimal | None:
    match = pattern.search(text)
    if not match:
        return None
    return parse_amount(match.group(1))


def first_last4(text: str) -> str | None:
    match = LAST4_RE.search(text)
    return match.group(1) if match else None


def first_customer(text: str) -> str | None:
    match = CUSTOMER_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def first_period(text: str) -> tuple[date, date] | None:
    for pattern in (PERIOD_YMD_RE, PERIOD_LONG_RE, PERIOD_RE):
        match = pattern.search(text)
        if match:
            return parse_indian_date(match.group(1)), parse_indian_date(match.group(2))
    return None


def amounts_in(text: str) -> list[Decimal]:
    return [parse_amount(item) for item in AMOUNT_RE.findall(text)]


def strip_amounts(text: str) -> str:
    cleaned = AMOUNT_RE.sub(" ", text)
    return " ".join(cleaned.split())
