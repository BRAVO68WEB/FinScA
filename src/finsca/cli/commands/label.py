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
from finsca.ledger.labeling import apply_labels, label_one

app = typer.Typer(help="Auto-label or manually set a transaction category.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_unlabeled()


@app.command("auto")
def auto_label() -> None:
    settings = Settings()
    with db_session() as session:
        counts = apply_labels(session, settings)
    console.print(
        f"labeled  rules={counts['rules']}  yaml={counts['yaml']}  compact={counts['compact']}"
    )


@app.command("set")
def set_label(
    txn: str = typer.Argument(..., help="id or unique prefix"),
    category: str = typer.Argument(..., help="dining, grocery, …"),
    remember: bool = typer.Option(False, "--remember"),
    match: str | None = typer.Option(None, "--match"),
) -> None:
    try:
        chosen = Category(category.strip().lower())
    except ValueError as exc:
        raise typer.BadParameter(f"unknown category: {category}") from exc
    if remember and not match:
        raise typer.BadParameter("--remember requires --match TOKEN")
    with db_session() as session:
        try:
            updated = label_one(session, txn, chosen, remember=match if remember else None)
        except KeyError as exc:
            console.print(f"[red]transaction not found or ambiguous: {txn}[/red]")
            raise typer.Exit(code=1) from exc
    if remember and match:
        console.print(f"remembered  {match}")
    console.print(
        f"{chosen.value}  {(updated.id or '')[:8]}  {format_inr(updated.amount)}  {updated.description_raw[:50]}"
    )


def list_unlabeled() -> None:
    with db_session() as session:
        rows = tx_repo.list_unlabeled(session)
        names = {item.id: item.display_name for item in account_repo.list_all(session)}
    if not rows:
        console.print("no unlabeled transactions")
        return
    table = Table(title="Unlabeled")
    table.add_column("id")
    table.add_column("date")
    table.add_column("amount", justify="right")
    table.add_column("account")
    table.add_column("description")
    for tx in rows[:50]:
        table.add_row(
            (tx.id or "")[:8],
            tx.posted_at.date().isoformat(),
            format_inr(tx.amount),
            names.get(tx.account_id, tx.account_id[:8]),
            tx.description_raw[:60],
        )
    console.print(table)
    extra = len(rows) - 50
    if extra > 0:
        console.print(f"… {extra} more")
    console.print("finsca label set ID dining --remember --match SWIGGY")
