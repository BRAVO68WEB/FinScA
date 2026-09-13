from __future__ import annotations

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.core.enums import Category
from finsca.core.money import format_inr
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.runtime import db_session
from finsca.ledger.apply import (
    ReviewDecision,
    apply_rules,
    link_self_transfers,
    resolve_transaction,
    review,
)

app = typer.Typer(help="Confirm credits as income or transfer, and link self-transfers.")

_INCOME_CATEGORIES = {
    "salary": Category.SALARY,
    "freelance": Category.FREELANCE,
    "business_income": Category.BUSINESS_INCOME,
    "interest": Category.INTEREST,
    "other": Category.OTHER,
}


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_pending()


@app.command("list")
def list_pending() -> None:
    with db_session() as session:
        rows = tx_repo.list_pending_review(session)
        names = {item.id: item.display_name for item in account_repo.list_all(session)}
    if not rows:
        console.print("no pending reviews")
        return
    table = Table(title="Pending income reviews")
    table.add_column("id")
    table.add_column("date")
    table.add_column("amount", justify="right")
    table.add_column("account")
    table.add_column("description")
    for tx in rows:
        table.add_row(
            (tx.id or "")[:8],
            tx.posted_at.date().isoformat(),
            format_inr(tx.amount),
            names.get(tx.account_id, tx.account_id[:8]),
            tx.description_raw[:60],
        )
    console.print(table)
    console.print(
        f"{len(rows)} pending  —  finsca review apply ID income|transfer [--always --match TOKEN]"
    )


@app.command("link")
def link() -> None:
    settings = Settings()
    with db_session() as session:
        paired = link_self_transfers(session, window_hours=settings.self_transfer_window_hours)
        ruled = apply_rules(session)
        left = len(tx_repo.list_pending_review(session))
    console.print(f"linked {paired} self-transfers  rules applied {ruled}  pending {left}")


@app.command("apply")
def apply_cmd(
    txn: str = typer.Argument(..., help="id or unique prefix"),
    decision: str = typer.Argument(..., help="income | transfer | skip"),
    category: str | None = typer.Option(None, "--category"),
    always: bool = typer.Option(False, "--always"),
    match: str | None = typer.Option(None, "--match", help="Token to remember with --always"),
) -> None:
    try:
        choice = ReviewDecision(decision.strip().lower())
    except ValueError as exc:
        raise typer.BadParameter("decision must be income, transfer, or skip") from exc
    cat = None
    if category:
        if category not in _INCOME_CATEGORIES:
            raise typer.BadParameter(f"category must be one of {', '.join(_INCOME_CATEGORIES)}")
        cat = _INCOME_CATEGORIES[category]
    if always:
        if choice is ReviewDecision.SKIP:
            raise typer.BadParameter("--always cannot be used with skip")
        if not match:
            raise typer.BadParameter("--always requires --match TOKEN")
    with db_session() as session:
        tx = resolve_transaction(session, txn)
        if tx is None or tx.id is None:
            console.print(f"[red]transaction not found or ambiguous: {txn}[/red]")
            raise typer.Exit(code=1)
        remember = match if always else None
        if remember:
            console.print(f"remembered  {remember}")
        updated = review(session, tx.id, choice, category=cat, remember=remember)
    console.print(
        f"{choice.value}  {(updated.id or '')[:8]}  {format_inr(updated.amount)}  {updated.description_raw[:50]}"
    )
