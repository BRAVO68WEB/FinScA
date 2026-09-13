from __future__ import annotations

from datetime import datetime

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.core.money import format_inr
from finsca.db.runtime import db_session
from finsca.ledger.report import latest_month, report_for
from finsca.reports.export import write_html
from finsca.reports.monthly import MonthReport

app = typer.Typer(help="Monthly cash-flow and health report.")


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    month: str | None = typer.Option(None, "--month", help="YYYY-MM"),
    html: bool = typer.Option(False, "--html"),
) -> None:
    if ctx.invoked_subcommand:
        return
    year, month_n = _parse_month(month)
    settings = Settings()
    with db_session() as session:
        if year is None or month_n is None:
            latest = latest_month(session)
            if latest is None:
                console.print("no transactions yet")
                raise typer.Exit(code=0)
            year, month_n = latest
        report = report_for(session, year, month_n)
    _print(report)
    if html:
        path = write_html(report, settings.reports_dir / f"{year:04d}-{month_n:02d}" / "report.html")
        console.print(f"html  {path}")


def _parse_month(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise typer.BadParameter("month must be YYYY-MM") from exc
    return parsed.year, parsed.month


def _print(report: MonthReport) -> None:
    console.print(f"[bold]FinScA report {report.year:04d}-{report.month:02d}[/bold]")
    flow = report.flow
    rate = f"{flow.savings_rate:.0%}" if flow.savings_rate is not None else "n/a"
    console.print(
        f"cash    in={format_inr(flow.inflow)}  out={format_inr(flow.outflow)}  "
        f"net={format_inr(flow.net)}  save={rate}"
    )
    _bars("categories", [(name, amount) for name, amount in report.categories])
    _bars("channels", [(ch.value, amount) for ch, amount in report.channels if amount > 0])
    salary = report.salary
    console.print(
        f"salary  n={salary.count}  day={salary.modal_day or '-'}  "
        f"last={salary.last_paid or '-'}  regular={salary.regular}"
    )
    gst = report.gst
    gst_rate = f"{gst.rate:.0%}" if gst.rate is not None else "n/a"
    console.print(f"gst     {format_inr(gst.gst)}  of {format_inr(gst.taxable)}  ({gst_rate})")
    console.print(f"emi     paid={format_inr(report.emi_paid)}  missed={report.missed_emis}")
    health = report.health
    console.print(f"health  {health.score if health.score is not None else 'n/a'}")
    bits = "  ".join(
        f"{key}={value if value is not None else 'n/a'}" for key, value in health.parts.items()
    )
    console.print(f"        {bits}")


def _bars(title: str, rows: list[tuple[str, object]]) -> None:
    if not rows:
        console.print(f"{title}  (none)")
        return
    table = Table(title=title)
    table.add_column("name")
    table.add_column("amount", justify="right")
    table.add_column("bar")
    peak = max((float(amount) for _, amount in rows), default=0) or 1
    for name, amount in rows:
        width = int(20 * float(amount) / peak)
        table.add_row(name, format_inr(amount), "█" * width)
    console.print(table)
