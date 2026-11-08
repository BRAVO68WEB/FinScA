"""Turn alert records into a ParsedBatch. Grammar lives in sms.templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from typing import Any

from finsca.core.enums import SourceKind
from finsca.ingest.errors import ParseError
from finsca.ingest.sms.fallback import parse_unmatched
from finsca.ingest.sms.templates import parse_alert
from finsca.ingest.types import ParsedBatch, ParsedLine

__all__ = ["AlertRecord", "alerts_to_batch", "parse_alert"]


@dataclass(frozen=True)
class AlertRecord:
    body: str
    address: str = ""
    sent_at: datetime | None = None


def alerts_to_batch(
    records: list[AlertRecord],
    kind: SourceKind,
    parser: str,
    *,
    complete: Any = None,
) -> ParsedBatch:
    lines: list[ParsedLine] = []
    warnings: list[str] = []
    for record in records:
        hit = parse_alert(record.body, sent_at=record.sent_at, address=record.address)
        if hit is None:
            hit = parse_unmatched(record.body, address=record.address, complete=complete)
        if hit is None:
            warnings.append(f"unparsed {parser}: {record.body[:80]}")
            continue
        lines.append(hit)
    if not lines:
        raise ParseError(f"no {parser} alerts parsed")
    return ParsedBatch(parser=parser, source_kind=kind, lines=lines, warnings=warnings)
