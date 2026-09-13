from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.email.mailbox import load_email
from finsca.ingest.errors import ParseError
from finsca.ingest.sms.templates import parse_alert
from finsca.ingest.types import ParsedBatch


def parse_email_file(path: Path) -> ParsedBatch:
    lines = []
    warnings: list[str] = []
    for record in load_email(path):
        blob = f"{record.subject}\n{record.body}"
        hit = parse_alert(blob, sent_at=record.sent_at, address=record.address)
        if hit is None:
            warnings.append(f"unparsed email: {(record.subject or record.body)[:80]}")
            continue
        lines.append(hit)
    if not lines:
        raise ParseError("no email alerts parsed")
    return ParsedBatch(parser="email", source_kind=SourceKind.EMAIL, lines=lines, warnings=warnings)
