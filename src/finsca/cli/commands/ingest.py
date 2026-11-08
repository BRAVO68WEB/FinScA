from __future__ import annotations

import typer

from pathlib import Path

from finsca.agents.pipeline import run_ingest, run_replay
from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.db.repositories import ingest_runs
from finsca.db.runtime import db_session

app = typer.Typer(help="Ingest inbox PDFs, email, and SMS dumps into the ledger.")


@app.callback(invoke_without_command=True)
def ingest(
    replay: str | None = typer.Option(None, "--replay", help="Re-read an archived run by id"),
) -> None:
    settings = Settings()
    settings.ensure_dirs()
    with db_session() as session:
        if replay:
            found = ingest_runs.find(session, replay)
            archive = Path(found.archive_path) if found and found.archive_path else None
            if found is None or archive is None or not archive.is_dir():
                console.print(f"[red]archive not found for {replay}[/red]")
                raise typer.Exit(code=1)
            summary = run_replay(session, settings, archive)
        else:
            summary = run_ingest(session, settings)
    if summary.empty:
        console.print("inbox empty")
        return
    console.print(f"run      {summary.run_id}")
    console.print(f"status   {summary.status.value}")
    console.print(
        f"parsed   {summary.parsed_count}  dupes={summary.dupe_count}  "
        f"pending reviews={summary.pending_review_count}"
    )
    if summary.skipped_files:
        console.print(
            f"skipped  {len(summary.skipped_files)}  "
            "(marketing mail / non-statement PDFs / empty statements)"
        )
    if summary.archive_path:
        console.print(f"archive  {summary.archive_path}")
    for item in summary.failed:
        console.print(f"[red]failed   {item.path.name}: {item.error}[/red]")
    if not summary.failed and not summary.skipped_files:
        console.print("inbox    pdf=0  email=0  sms=0")
