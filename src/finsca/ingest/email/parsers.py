"""Bank-alert mail. Invoice and salary mail use the same alert grammar for now."""

from __future__ import annotations

from pathlib import Path

from finsca.core.enums import SourceKind
from finsca.ingest.alerts import alerts_to_batch
from finsca.ingest.email.mailbox import load_email
from finsca.ingest.errors import ParseError, SkipFile
from finsca.ingest.types import ParsedBatch


def parse_email(path: Path, *, complete: object | None = None) -> ParsedBatch:
    try:
        return alerts_to_batch(load_email(path), SourceKind.EMAIL, "email", complete=complete)
    except ParseError as exc:
        if str(exc).startswith("no email alerts"):
            raise SkipFile("no transaction alert in email") from exc
        raise
