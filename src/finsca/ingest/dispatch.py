from __future__ import annotations

from pathlib import Path

from finsca.config.passwords import candidates_for, load_store
from finsca.config.settings import Settings
from finsca.core.enums import SourceKind
from finsca.ingest.alerts import alerts_to_batch
from finsca.ingest.detect import detect_bank
from finsca.ingest.email.mailbox import load_email
from finsca.ingest.errors import ParseError
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.text_extract import extract_text
from finsca.ingest.sms.loaders import load_sms
from finsca.ingest.types import ParsedBatch


def parse_inbox_file(path: Path, kind: SourceKind, settings: Settings | None = None) -> ParsedBatch:
    if kind is SourceKind.PDF:
        cfg = settings or Settings()
        passwords = candidates_for(path.name, load_store(cfg.data_dir / "pdf_passwords.yaml"), extra=cfg.pdf_password)
        text = extract_text(path, passwords)
        if not text:
            raise ParseError("PDF contained no extractable text")
        batch = parse_statement(text, detect_bank(text))
        if not batch.lines:
            raise ParseError("no transactions parsed")
        return batch
    if kind is SourceKind.SMS:
        return alerts_to_batch(load_sms(path), SourceKind.SMS, "sms")
    if kind is SourceKind.EMAIL:
        return alerts_to_batch(load_email(path), SourceKind.EMAIL, "email")
    raise ParseError(f"unsupported inbox kind: {kind}")
