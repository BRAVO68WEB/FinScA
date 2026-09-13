from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from finsca.archive.mover import archive_successes, write_error_sidecar
from finsca.config.settings import Settings
from finsca.core.enums import IngestStatus
from finsca.db.repositories import ingest_runs
from finsca.ingest.detect import detect_bank, file_digest, list_inbox_pdfs
from finsca.ingest.pdf.base import parse_statement
from finsca.ingest.pdf.text_extract import extract_text
from finsca.ingest.persist import persist_batch
from finsca.ingest.types import IngestFileResult, IngestSummary


class ParseError(ValueError):
    pass


def run_ingest(session: Session, settings: Settings) -> IngestSummary:
    pdfs = list_inbox_pdfs(settings.inbox_dir)
    if not pdfs:
        return IngestSummary(empty=True)

    run = ingest_runs.start(session)
    results = [_ingest_one(session, path, run.id) for path in pdfs]
    successes = [item for item in results if item.error is None]
    failures = [item for item in results if item.error is not None]

    archive_path = None
    if successes:
        archive_path = archive_successes(successes, settings.archive_dir, run.id)

    parsed = sum(item.tx_count for item in successes)
    dupes = sum(item.dupe_count for item in successes)
    pending = sum(item.pending_review for item in successes)
    status = _status(successes, failures)
    error = failures[0].error if failures and not successes else None
    ingest_runs.finish(
        session,
        run,
        status=status,
        parsed_count=parsed,
        dupe_count=dupes,
        pending_review_count=pending,
        archive_path=archive_path,
        error=error,
    )
    for item in results:
        ingest_runs.add_file(session, run.id, item)

    return IngestSummary(
        run_id=run.id,
        status=status,
        parsed_count=parsed,
        dupe_count=dupes,
        pending_review_count=pending,
        archive_path=archive_path,
        files=results,
    )


def _ingest_one(session: Session, path: Path, run_id: str) -> IngestFileResult:
    digest = file_digest(path)
    try:
        text = extract_text(path)
        if not text:
            raise ParseError("PDF contained no extractable text")
        bank = detect_bank(text)
        batch = parse_statement(text, bank)
        if not batch.lines:
            raise ParseError("no transactions parsed")
        persisted = persist_batch(session, batch, run_id)
        warning = "; ".join(batch.warnings) if batch.warnings else None
        return IngestFileResult(
            path=path,
            sha256=digest,
            parser=batch.parser,
            tx_count=persisted.inserted,
            dupe_count=persisted.dupes,
            pending_review=persisted.pending_review,
            warning=warning,
        )
    except Exception as exc:
        write_error_sidecar(path, str(exc))
        return IngestFileResult(path=path, sha256=digest, error=str(exc))


def _status(successes: list[IngestFileResult], failures: list[IngestFileResult]) -> IngestStatus:
    if successes and failures:
        return IngestStatus.PARTIAL
    if successes:
        return IngestStatus.SUCCESS
    return IngestStatus.FAILED
