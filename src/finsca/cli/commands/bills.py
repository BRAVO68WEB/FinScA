from __future__ import annotations

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.core.enums import AccountType, Intent
from finsca.core.money import format_inr
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.runtime import db_session
from finsca.finance.cc_bills import parse_bill_pay
from finsca.ledger.bills import inject_cc_bills

app = typer.Typer(help="Credit-card bill payments from bank narrations.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_bills()


@app.command("list")
def list_bills() -> None:
    with db_session() as session:
        cards = [item for item in account_repo.list_all(session) if item.type is AccountType.CREDIT_CARD]
        pays = [
            tx
            for tx in tx_repo.list_all(session)
            if tx.intent is Intent.SELF_TRANSFER and parse_bill_pay(tx.description_raw)
        ]
    if not cards and not pays:
        console.print("no CC bills yet  —  finsca bills inject")
        return
    table = Table(title="CC bill payments")
    table.add_column("date")
    table.add_column("amount", justify="right")
    table.add_column("description")
    for tx in pays:
        table.add_row(tx.posted_at.date().isoformat(), format_inr(tx.amount), tx.description_raw[:70])
    console.print(table)
    console.print(f"{len(pays)} payments  across {len(cards)} card accounts")


@app.command("inject")
def inject_cmd() -> None:
    with db_session() as session:
        marked = inject_cc_bills(session)
    console.print(f"injected {marked} CC bill payments")
