"""Strip account numbers, PANs, VPA local-parts, and phone numbers before an LLM call."""

from __future__ import annotations

import re

_LONG_DIGITS = re.compile(r"\d{6,}")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_VPA = re.compile(r"\b([A-Za-z0-9._-]{2,})@([A-Za-z][A-Za-z0-9]{2,})\b")
_PHONE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b")


def redact(text: str) -> str:
    cleaned = _PAN.sub("XXXXX0000X", text)
    cleaned = _VPA.sub(lambda match: f"XXXX@{match.group(2)}", cleaned)
    cleaned = _PHONE.sub("XXXXXXXXXX", cleaned)
    return _LONG_DIGITS.sub("XXXX", cleaned)
