from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from finsca.core.clock import utcnow
from finsca.ingest.types import IngestFileResult


def write_error_sidecar(path: Path, error: str) -> Path:
    sidecar = path.with_name(path.name + ".error.json")
    sidecar.write_text(json.dumps({"file": path.name, "error": error}, indent=2), encoding="utf-8")
    return sidecar


def planned_archive_dir(archive_dir: Path, run_id: str, *, when: date | None = None) -> Path:
    day = when or utcnow().date()
    return archive_dir / f"{day.isoformat()}_run_{run_id[:12]}"


def archive_successes(
    files: list[IngestFileResult],
    dest: Path,
    run_id: str,
) -> list[IngestFileResult]:
    dest.mkdir(parents=True, exist_ok=True)
    updated: list[IngestFileResult] = []
    archived: list[dict[str, object]] = []
    for item in files:
        target = dest / item.path.name
        shutil.move(str(item.path), target)
        stored = item.model_copy(update={"archived_as": str(target)})
        updated.append(stored)
        archived.append(
            {
                "original": item.path.name,
                "sha256": item.sha256,
                "parser": item.parser,
                "tx_count": item.tx_count,
                "warning": item.warning,
            }
        )
    (dest / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "files": archived}, indent=2),
        encoding="utf-8",
    )
    return updated
