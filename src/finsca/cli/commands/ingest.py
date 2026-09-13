from __future__ import annotations

import typer

from finsca.agents.pipeline import run_ingest
from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.db.runtime import db_session

app = typer.Typer(help="Ingest inbox PDFs into the ledger and archive them.")


@app.callback(invoke_without_command=True)
def ingest() -> None:
    settings = Settings()
    settings.ensure_dirs()
    with db_session() as session:
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
    if summary.archive_path:
        console.print(f"archive  {summary.archive_path}")
    for item in summary.failed:
        console.print(f"[red]failed   {item.path.name}: {item.error}[/red]")
    if not summary.failed:
        console.print("inbox    pdf=0")
