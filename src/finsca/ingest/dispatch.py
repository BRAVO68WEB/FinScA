from __future__ import annotations

import re
from pathlib import Path

from finsca.config.passwords import candidates_for, load_store
from finsca.config.settings import Settings
from finsca.core.enums import SourceKind
from finsca.ingest.alerts import alerts_to_batch
from finsca.ingest.detect import detect_bank
from finsca.ingest.email.mailbox import load_email
from finsca.ingest.errors import ParseError, SkipFile
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.text_extract import extract_text
from finsca.ingest.sms.loaders import load_sms
from finsca.ingest.types import ParsedBatch

_NOISE_NAME = re.compile(
    r"(kfs|mitc|key.?facts|digiremi|ipz460-funds|ipz460-securities|"
    r"payments-noreply_google|creditcardkfs|creditcardmitc)",
    re.I,
)
_STATEMENTISH = re.compile(
    r"(statement|estatement|e-statement|transaction history|credit card)",
    re.I,
)


def parse_inbox_file(path: Path, kind: SourceKind, settings: Settings | None = None) -> ParsedBatch:
    if kind is SourceKind.PDF:
        return _parse_pdf(path, settings or Settings())
    if kind is SourceKind.SMS:
        return alerts_to_batch(load_sms(path), SourceKind.SMS, "sms")
    if kind is SourceKind.EMAIL:
        return _parse_email(path)
    raise ParseError(f"unsupported inbox kind: {kind}")


def _parse_pdf(path: Path, settings: Settings) -> ParsedBatch:
    if _NOISE_NAME.search(path.name):
        raise SkipFile("not a bank/card statement")
    passwords = candidates_for(path.name, load_store(settings.data_dir / "pdf_passwords.yaml"), extra=settings.pdf_password)
    text = extract_text(path, passwords)
    if not text:
        raise ParseError("PDF contained no extractable text")
    batch = parse_statement(text, detect_bank(text, path.name), filename=path.name)
    if batch.lines:
        return batch
    if _STATEMENTISH.search(path.name) or _STATEMENTISH.search(text[:2000]):
        raise SkipFile("statement has no extractable transactions")
    raise SkipFile("not a bank/card statement")


def _parse_email(path: Path) -> ParsedBatch:
    try:
        return alerts_to_batch(load_email(path), SourceKind.EMAIL, "email")
    except ParseError as exc:
        if str(exc).startswith("no email alerts"):
            raise SkipFile("no transaction alert in email") from exc
        raise
