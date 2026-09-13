from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.core.enums import IncomeReview
from finsca.db.runtime import db_session
from finsca.db.schema import IngestRun, Transaction

INBOX_KINDS = ("pdf", "email", "sms")


@dataclass(frozen=True)
class StatusView:
    run_count: int
    last_run_id: str | None
    last_run_status: str | None
    pending_reviews: int
    inbox: dict[str, int]


def _inbox_count(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for path in folder.iterdir() if path.is_file() and path.name != ".gitkeep")


def collect_status(settings: Settings, session: Session) -> StatusView:
    run_count = session.scalar(select(func.count()).select_from(IngestRun)) or 0
    last = session.scalar(select(IngestRun).order_by(IngestRun.started_at.desc()).limit(1))
    pending = session.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.income_review == IncomeReview.PENDING.value)
    ) or 0
    inbox = {
        kind: _inbox_count(settings.inbox_dir / kind) for kind in INBOX_KINDS
    }
    return StatusView(
        run_count=run_count,
        last_run_id=last.id if last else None,
        last_run_status=last.status if last else None,
        pending_reviews=pending,
        inbox=inbox,
    )


def print_status() -> None:
    settings = Settings()
    settings.ensure_dirs()
    with db_session() as session:
        view = collect_status(settings, session)

    console.print("[bold]FinScA[/bold]")
    if view.run_count == 0:
        console.print("no runs yet")
    else:
        console.print(f"last run  {view.last_run_id}  ({view.last_run_status})")
        console.print(f"runs      {view.run_count}")
    inbox = "  ".join(f"{kind}={view.inbox[kind]}" for kind in INBOX_KINDS)
    console.print(f"inbox     {inbox}")
    console.print(f"pending reviews  {view.pending_reviews}")
