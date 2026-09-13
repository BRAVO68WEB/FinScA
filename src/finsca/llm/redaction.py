"""Strip account numbers and long digit runs before an LLM call."""

from __future__ import annotations

import re

_LONG_DIGITS = re.compile(r"\d{6,}")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def redact(text: str) -> str:
    cleaned = _PAN.sub("XXXXX0000X", text)
    return _LONG_DIGITS.sub("XXXX", cleaned)
