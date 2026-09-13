"""Archive inbox files after a successful or partial ingest run."""

from pathlib import Path

from finsca.archive.mover import archive_successes
from finsca.ingest.types import IngestFileResult


def archive(files: list[IngestFileResult], archive_dir: Path, run_id: str) -> Path:
    return archive_successes(files, archive_dir, run_id)
