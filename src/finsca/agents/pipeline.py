"""Ingest order and error policy. Stage work lives in subagents."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from finsca.agents.context import (
    ArchiveInput,
    IngestRunCtx,
    NormalizeInput,
    ParseInput,
    PersistInput,
    StageInput,
)
from finsca.agents.registry import get
from finsca.archive.mover import planned_archive_dir, write_error_sidecar
from finsca.config.settings import Settings
from finsca.core.enums import IngestStatus, SourceKind
from finsca.core.ids import file_sha256
from finsca.db.repositories import ingest_runs
from finsca.db.repositories import transactions as tx_repo
from finsca.ingest.detect import list_archive_files, list_inbox_files
from finsca.ingest.errors import ParseError, SkipFile
from finsca.ingest.types import IngestFileResult, IngestSummary
from finsca.ledger.apply import link_self_transfers
from finsca.ledger.bills import inject_cc_bills

_PARSE_AGENT = {
    SourceKind.PDF: "ingest_pdf",
    SourceKind.EMAIL: "ingest_email",
    SourceKind.SMS: "ingest_sms",
}


def run_replay(session: Session, settings: Settings, archive_dir: Path) -> IngestSummary:
    """Re-parse an archive in place. Files stay where they are."""
    return run_ingest(
        session,
        settings,
        sources=list_archive_files(archive_dir),
        archive_files=False,
    )


def run_ingest(
    session: Session,
    settings: Settings,
    *,
    sources: list[tuple[Path, SourceKind]] | None = None,
    archive_files: bool = True,
) -> IngestSummary:
    incoming = list_inbox_files(settings.inbox_dir) if sources is None else sources
    if not incoming:
        return IngestSummary(empty=True)

    run = ingest_runs.start(session)
    ctx = IngestRunCtx(settings=settings, session=session, run_id=run.id)
    results = [_ingest_one(ctx, path, kind) for path, kind in incoming]
    successes = [item for item in results if item.error is None and not item.skipped]
    skipped = [item for item in results if item.skipped]
    failures = [item for item in results if item.error is not None]
    movable = [*successes, *skipped]

    archive_path = (
        planned_archive_dir(settings.archive_dir, run.id) if archive_files and movable else None
    )
    parsed = sum(item.tx_count for item in successes)
    dupes = sum(item.dupe_count for item in successes)
    linked = 0
    if successes:
        get("normalize").run(ctx, NormalizeInput(inserted=parsed, dupes=dupes))
        linked = link_self_transfers(session, window_hours=settings.self_transfer_window_hours)
        get("confirm").run(ctx, StageInput())
        get("labeler").run(ctx, StageInput())
        get("loans").run(ctx, StageInput())
        inject_cc_bills(session)
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

    if archive_files and movable and archive_path is not None:
        archived = get("archive").run(
            ctx,
            ArchiveInput(files=movable, dest=archive_path, run_id=run.id),
        )
        by_name = {item.path.name: item for item in archived.output.files}
        results = [
            by_name.get(item.path.name, item) if item.error is None else item for item in results
        ]

    return IngestSummary(
        run_id=run.id,
        status=status,
        parsed_count=parsed,
        dupe_count=dupes,
        pending_review_count=pending,
        archive_path=archive_path,
        files=results,
    )


def _ingest_one(ctx: IngestRunCtx, path: Path, kind: SourceKind) -> IngestFileResult:
    digest = file_sha256(path)
    relpath = _relpath(path, ctx.settings.inbox_dir)
    try:
        with ctx.session.begin_nested():
            parsed = get(_PARSE_AGENT[kind]).run(ctx, ParseInput(path=path, kind=kind))
            saved = get("ledger").run(
                ctx,
                PersistInput(batch=parsed.output.batch, run_id=ctx.run_id or ""),
            )
        warning = "; ".join(parsed.output.batch.warnings) if parsed.output.batch.warnings else None
        return IngestFileResult(
            path=path,
            sha256=digest,
            parser=parsed.output.batch.parser,
            tx_count=saved.output.inserted,
            dupe_count=saved.output.dupes,
            pending_review=saved.output.pending_review,
            warning=warning,
            kind=kind,
            relpath=relpath,
        )
    except SkipFile as exc:
        sidecar = path.with_name(path.name + ".error.json")
        sidecar.unlink(missing_ok=True)
        return IngestFileResult(
            path=path,
            sha256=digest,
            skipped=True,
            warning=str(exc),
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
    if failures and successes:
        return IngestStatus.PARTIAL
    if failures:
        return IngestStatus.FAILED
    return IngestStatus.SUCCESS
