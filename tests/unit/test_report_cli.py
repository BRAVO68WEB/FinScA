from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session
from typer.testing import CliRunner

from finsca.cli.app import app
from finsca.core.enums import AccountType, Category, Channel, Intent, SourceKind
from finsca.core.models import Account, Transaction
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo

runner = CliRunner()


def _seed_august(db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, last4="4004"),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            amount=Decimal("80000.00"),
            description_raw="SALARY",
            source_kind=SourceKind.PDF,
            intent=Intent.INCOME,
            category=Category.SALARY,
            channel=Channel.NEFT,
        ),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
            amount=Decimal("-1200.00"),
            description_raw="SWIGGY",
            source_kind=SourceKind.PDF,
            intent=Intent.EXPENSE,
            category=Category.DINING,
            channel=Channel.UPI,
        ),
    )
    db_session.commit()


def test_report_prints_cashflow(data_dir: Path, db_session: Session) -> None:
    account = account_repo.add(
        db_session,
        Account(display_name="AXIS 4004", type=AccountType.SAVINGS, last4="4004"),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            amount=Decimal("80000.00"),
            description_raw="SALARY",
            source_kind=SourceKind.PDF,
            intent=Intent.INCOME,
            category=Category.SALARY,
            channel=Channel.NEFT,
        ),
    )
    tx_repo.add_event(
        db_session,
        Transaction(
            account_id=account.id or "",
            posted_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
            amount=Decimal("-1200.00"),
            description_raw="SWIGGY",
            source_kind=SourceKind.PDF,
            intent=Intent.EXPENSE,
            category=Category.DINING,
            channel=Channel.UPI,
        ),
    )
    db_session.commit()
    result = runner.invoke(app, ["report", "--month", "2026-08"])
    assert result.exit_code == 0, result.output
    assert "80000.00" in result.output
    assert "1200.00" in result.output
    assert "dining" in result.output
    assert "health" in result.output


def test_report_html_contains_the_category(data_dir: Path, db_session: Session) -> None:
    _seed_august(db_session)
    result = runner.invoke(app, ["report", "--month", "2026-08", "--html"])
    assert result.exit_code == 0, result.output
    html = (data_dir / "reports" / "2026-08" / "report.html").read_text(encoding="utf-8")
    assert "dining" in html


def test_report_appends_a_narrative_paragraph(
    data_dir: Path,
    db_session: Session,
    monkeypatch,
) -> None:
    _seed_august(db_session)
    monkeypatch.setattr(
        "finsca.cli.commands.report.month_narrative",
        lambda _report: "Savings is the weak spot.",
    )
    result = runner.invoke(app, ["report", "--month", "2026-08"])
    assert result.exit_code == 0, result.output
    assert result.output.index("health") < result.output.index("Savings is the weak spot.")


def test_report_falls_back_to_rich_bars_without_plotext(
    data_dir: Path,
    db_session: Session,
    monkeypatch,
) -> None:
    _seed_august(db_session)
    monkeypatch.setattr("finsca.cli.commands.report.plot_bars", lambda *_args, **_kwargs: None)
    result = runner.invoke(app, ["report", "--month", "2026-08"])
    assert result.exit_code == 0, result.output
    assert "dining" in result.output
    assert "█" in result.output
