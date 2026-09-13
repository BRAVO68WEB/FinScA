from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from finsca.archive.mover import archive_successes, planned_archive_dir, write_error_sidecar
from finsca.config.settings import Settings
from finsca.core.enums import IngestStatus, SourceKind
from finsca.core.ids import file_sha256
from finsca.db.repositories import ingest_runs
from finsca.ingest.detect import list_inbox_files
from finsca.ingest.dispatch import parse_inbox_file
from finsca.ingest.errors import ParseError
from finsca.db.repositories import transactions as tx_repo
from finsca.ledger.apply import apply_rules, link_self_transfers
from finsca.ingest.persist import persist_batch
from finsca.ingest.types import IngestFileResult, IngestSummary


def run_ingest(session: Session, settings: Settings) -> IngestSummary:
    incoming = list_inbox_files(settings.inbox_dir)
    if not incoming:
        return IngestSummary(empty=True)

    run = ingest_runs.start(session)
    results = [
        _ingest_one(session, path, kind, run.id, settings.inbox_dir) for path, kind in incoming
    ]
    successes = [item for item in results if item.error is None]
    failures = [item for item in results if item.error is not None]

    archive_path = planned_archive_dir(settings.archive_dir, run.id) if successes else None
    parsed = sum(item.tx_count for item in successes)
    dupes = sum(item.dupe_count for item in successes)
    linked = 0
    if successes:
        linked = link_self_transfers(session, window_hours=settings.self_transfer_window_hours)
        apply_rules(session)
    pending = len(tx_repo.list_pending_review(session))
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
        self_transfer_count=linked,
    )
    for item in results:
        ingest_runs.add_file(session, run.id, item)
    session.commit()

    if successes and archive_path is not None:
        archived = archive_successes(successes, archive_path, run.id)
        by_name = {item.path.name: item for item in archived}
        results = [by_name.get(item.path.name, item) if item.error is None else item for item in results]

    return IngestSummary(
        run_id=run.id,
        status=status,
        parsed_count=parsed,
        dupe_count=dupes,
        pending_review_count=pending,
        archive_path=archive_path,
        files=results,
    )


def _ingest_one(
    session: Session,
    path: Path,
    kind: SourceKind,
    run_id: str,
    inbox_dir: Path,
) -> IngestFileResult:
    digest = file_sha256(path)
    relpath = _relpath(path, inbox_dir)
    try:
        with session.begin_nested():
            batch = parse_inbox_file(path, kind)
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
            kind=kind,
            relpath=relpath,
        )
    except ParseError as exc:
        write_error_sidecar(path, str(exc))
        return IngestFileResult(path=path, sha256=digest, error=str(exc), kind=kind, relpath=relpath)


def _relpath(path: Path, inbox_dir: Path) -> str:
    try:
        return str(path.relative_to(inbox_dir))
    except ValueError:
        return path.name


def _status(successes: list[IngestFileResult], failures: list[IngestFileResult]) -> IngestStatus:
    if successes and failures:
        return IngestStatus.PARTIAL
    if successes:
        return IngestStatus.SUCCESS
    return IngestStatus.FAILED
