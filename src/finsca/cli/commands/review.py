from __future__ import annotations

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.core.enums import Category, IncomeReview, Intent
from finsca.core.models import Transaction
from finsca.core.money import format_inr
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories import rules as rule_repo
from finsca.db.repositories import transactions as tx_repo
from finsca.db.runtime import db_session
from finsca.finance.apply import apply_rules, link_self_transfers, pending_credits

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
        rows = pending_credits(session)
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
    console.print(f"{len(rows)} pending  —  finsca review apply ID income|transfer [--always]")


@app.command("link")
def link() -> None:
    settings = Settings()
    with db_session() as session:
        paired = link_self_transfers(session, window_hours=settings.self_transfer_window_hours)
        ruled = apply_rules(session)
        left = len(pending_credits(session))
    console.print(f"linked {paired} self-transfers  rules applied {ruled}  pending {left}")


@app.command("apply")
def apply(
    txn: str = typer.Argument(..., help="id or unique prefix"),
    decision: str = typer.Argument(..., help="income | transfer | skip"),
    category: str | None = typer.Option(None, "--category"),
    always: bool = typer.Option(False, "--always"),
    match: str | None = typer.Option(None, "--match", help="Token to remember with --always"),
) -> None:
    choice = decision.strip().lower()
    if choice not in {"income", "transfer", "skip"}:
        raise typer.BadParameter("decision must be income, transfer, or skip")
    cat = None
    if category:
        if category not in _INCOME_CATEGORIES:
            raise typer.BadParameter(f"category must be one of {', '.join(_INCOME_CATEGORIES)}")
        cat = _INCOME_CATEGORIES[category]
    with db_session() as session:
        tx = _resolve_tx(session, txn)
        if tx.id is None:
            raise typer.Exit(code=1)
        if choice == "income":
            updated = tx_repo.apply_review(
                session,
                tx.id,
                intent=Intent.INCOME,
                income_review=IncomeReview.INCOME,
                exclude_from_cashflow=False,
                category=cat or Category.OTHER,
            )
        elif choice == "transfer":
            updated = tx_repo.apply_review(
                session,
                tx.id,
                intent=Intent.TRANSFER,
                income_review=IncomeReview.TRANSFER,
                exclude_from_cashflow=True,
            )
        else:
            updated = tx_repo.apply_review(
                session,
                tx.id,
                intent=tx.intent,
                income_review=IncomeReview.SKIPPED,
                exclude_from_cashflow=tx.exclude_from_cashflow,
            )
        if always and choice in {"income", "transfer"}:
            token = match or _default_match(tx)
            rule_repo.add(
                session,
                match_field="description_contains",
                match_value=token,
                intent=Intent.INCOME if choice == "income" else Intent.TRANSFER,
                category=cat,
            )
            console.print(f"remembered  {token}")
    console.print(
        f"{choice}  {(updated.id or '')[:8]}  {format_inr(updated.amount)}  {updated.description_raw[:50]}"
    )


def _resolve_tx(session, token: str) -> Transaction:
    needle = token.strip()
    rows = pending_credits(session)
    hits = [tx for tx in rows if tx.id and tx.id.startswith(needle)]
    if len(hits) == 1:
        return hits[0]
    all_rows = tx_repo.list_all(session)
    hits = [tx for tx in all_rows if tx.id and tx.id.startswith(needle)]
    if len(hits) != 1:
        console.print(f"[red]transaction not found or ambiguous: {token}[/red]")
        raise typer.Exit(code=1)
    return hits[0]


def _default_match(tx: Transaction) -> str:
    words = [part for part in tx.description_raw.replace("/", " ").split() if part.isalpha() and len(part) > 3]
    if words:
        return " ".join(words[:3])
    return (tx.description_norm or tx.description_raw)[:24]
