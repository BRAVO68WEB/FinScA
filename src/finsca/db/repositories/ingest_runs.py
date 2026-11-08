from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from finsca.core.clock import utcnow
from finsca.core.enums import IngestStatus
from finsca.core.ids import new_id
from finsca.db import schema as tables
from finsca.ingest.types import IngestFileResult


def find(session: Session, token: str) -> tables.IngestRun | None:
    """Full id, or the 12-character prefix used in the archive folder name."""
    needle = token.strip()
    if not needle:
        return None
    exact = session.get(tables.IngestRun, needle)
    if exact is not None:
        return exact
    hits: list[tables.IngestRun] = []
    for row in session.scalars(select(tables.IngestRun)).all():
        folder = Path(row.archive_path).name if row.archive_path else ""
        if row.id.startswith(needle) or (folder and needle in folder):
            hits.append(row)
    if len(hits) == 1:
        return hits[0]
    return None


def start(session: Session) -> tables.IngestRun:
    row = tables.IngestRun(id=new_id(), status=IngestStatus.RUNNING.value)
    session.add(row)
    session.flush()
    return row


def add_file(session: Session, run_id: str, item: IngestFileResult) -> tables.IngestFile:
    row = tables.IngestFile(
        id=new_id(),
        ingest_run_id=run_id,
        original_name=item.path.name,
        sha256=item.sha256,
        kind=(item.kind.value if item.kind else "pdf"),
        parser=item.parser,
        tx_count=item.tx_count,
        warning=item.warning or item.error,
        archived_as=item.archived_as,
    )
    session.add(row)
    session.flush()
    return row


def finish(
    session: Session,
    run: tables.IngestRun,
    *,
    status: IngestStatus,
    parsed_count: int,
    dupe_count: int,
    pending_review_count: int,
    archive_path: Path | None,
    error: str | None = None,
    self_transfer_count: int = 0,
) -> tables.IngestRun:
    run.finished_at = utcnow()
    run.status = status.value
    run.parsed_count = parsed_count
    run.dupe_count = dupe_count
    run.self_transfer_count = self_transfer_count
    run.pending_review_count = pending_review_count
    run.archive_path = str(archive_path) if archive_path else None
    run.error = error
    session.flush()
    return run
