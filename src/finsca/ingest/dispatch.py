from __future__ import annotations

import re
from pathlib import Path

from finsca.config.passwords import candidates_for, load_store
from finsca.config.settings import Settings
from finsca.core.enums import SourceKind
from finsca.ingest.alerts import alerts_to_batch
from finsca.ingest.detect import detect_bank, looks_like_statement
from finsca.ingest.email.parsers import parse_email
from finsca.ingest.errors import ParseError, SkipFile
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.text_extract import extract_text
from finsca.ingest.sms.loaders import load_sms
from finsca.ingest.types import ParsedBatch
from finsca.llm.router import compact_complete

_NOISE_NAME = re.compile(
    r"(kfs|mitc|key.?facts|digiremi|ipz460-funds|ipz460-securities|"
    r"payments-noreply_google|creditcardkfs|creditcardmitc)",
    re.I,
)


def parse_inbox_file(path: Path, kind: SourceKind, settings: Settings | None = None) -> ParsedBatch:
    cfg = settings or Settings()
    complete = compact_complete(cfg)
    if kind is SourceKind.PDF:
        return _parse_pdf(path, cfg, complete)
    if kind is SourceKind.SMS:
        return alerts_to_batch(load_sms(path), SourceKind.SMS, "sms", complete=complete)
    if kind is SourceKind.EMAIL:
        return parse_email(path, complete=complete)
    raise ParseError(f"unsupported inbox kind: {kind}")


def _parse_pdf(path: Path, settings: Settings, complete: object | None) -> ParsedBatch:
    if _NOISE_NAME.search(path.name):
        raise SkipFile("not a bank/card statement")
    passwords = candidates_for(path.name, load_store(settings.data_dir / "pdf_passwords.yaml"), extra=settings.pdf_password)
    text = extract_text(path, passwords)
    if not text:
        raise ParseError("PDF contained no extractable text")
    batch = parse_statement(
        text,
        detect_bank(text, path.name),
        filename=path.name,
        complete=complete,
    )
    if batch.lines:
        return batch
    if looks_like_statement(text, path.name):
        raise SkipFile("statement has no extractable transactions")
    raise SkipFile("not a bank/card statement")


