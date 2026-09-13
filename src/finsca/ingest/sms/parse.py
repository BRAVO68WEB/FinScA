from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.errors import ParseError
from finsca.ingest.sms.loaders import load_sms
from finsca.ingest.sms.templates import parse_alert
from finsca.ingest.types import ParsedBatch


def parse_sms_file(path: Path) -> ParsedBatch:
    lines = []
    warnings: list[str] = []
    for record in load_sms(path):
        hit = parse_alert(record.body, sent_at=record.sent_at, address=record.address)
        if hit is None:
            warnings.append(f"unparsed sms: {record.body[:80]}")
            continue
        lines.append(hit)
    if not lines:
        raise ParseError("no SMS alerts parsed")
    return ParsedBatch(parser="sms", source_kind=SourceKind.SMS, lines=lines, warnings=warnings)
