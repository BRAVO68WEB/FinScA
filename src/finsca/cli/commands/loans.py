from __future__ import annotations

from datetime import datetime, timezone

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.core.enums import EmiStatus, LoanStatus
from finsca.core.models import Loan
from finsca.core.money import format_inr, parse_inr
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import loans as loan_repo
from finsca.db.runtime import db_session
from finsca.ledger.loans import add_loan, match_all

app = typer.Typer(help="Track EMIs and active loans.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_loans()


@app.command("list")
def list_loans() -> None:
    with db_session() as session:
        rows = loan_repo.list_all(session)
        if not rows:
            console.print("no loans yet")
            return
        table = Table(title="Loans")
        table.add_column("id")
        table.add_column("name")
        table.add_column("lender")
        table.add_column("emi", justify="right")
        table.add_column("day")
        table.add_column("status")
        table.add_column("last / next")
        for loan in rows:
            occ = loan_repo.list_occurrences(session, loan.id or "")
            latest = occ[-1].status.value if occ else "-"
            table.add_row(
                (loan.id or "")[:8],
                loan.name,
                loan.lender,
                format_inr(loan.emi),
                str(loan.emi_day or "-"),
                loan.status.value,
                latest,
            )
        console.print(table)


@app.command("add")
def add_cmd(
    name: str = typer.Option(..., "--name"),
    lender: str = typer.Option(..., "--lender"),
    emi: str = typer.Option(..., "--emi"),
    principal: str = typer.Option("0", "--principal"),
    day: int | None = typer.Option(None, "--day"),
    tenure: int | None = typer.Option(None, "--tenure"),
    account: str | None = typer.Option(None, "--account"),
    start: str | None = typer.Option(None, "--start", help="YYYY-MM-DD"),
) -> None:
    start_date = None
    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    with db_session() as session:
        account_id = None
        if account:
            found = account_repo.resolve(session, account)
            if found is None or found.id is None:
                console.print(f"[red]account not found: {account}[/red]")
                raise typer.Exit(code=1)
            account_id = found.id
        loan = add_loan(
            session,
            Loan(
                name=name,
                lender=lender,
                principal=parse_inr(principal),
                emi=parse_inr(emi),
                emi_day=day,
                tenure_months=tenure,
                start_date=start_date,
                account_id=account_id,
            ),
        )
        occ = loan_repo.list_occurrences(session, loan.id or "")
        paid = sum(1 for item in occ if item.status is EmiStatus.PAID)
    console.print(f"added  {loan.name}  id={(loan.id or '')[:8]}  emi={format_inr(loan.emi)}  matched={paid}")


@app.command("match")
def match_cmd() -> None:
    with db_session() as session:
        paid = match_all(session)
    console.print(f"matched {paid} EMI payments")


@app.command("close")
def close_cmd(loan: str = typer.Argument(...)) -> None:
    with db_session() as session:
        found = loan_repo.resolve(session, loan)
        if found is None or found.id is None:
            console.print(f"[red]loan not found: {loan}[/red]")
            raise typer.Exit(code=1)
        closed = loan_repo.close(session, found.id)
    console.print(f"closed  {closed.name}  ({LoanStatus.CLOSED.value})")
