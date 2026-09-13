from __future__ import annotations

import typer
from rich.table import Table
from sqlalchemy.orm import Session

from finsca.cli.render import console
from finsca.core.enums import AccountType, MonthSource
from finsca.core.models import Account, AccountMonth
from finsca.core.money import format_inr, parse_inr
from finsca.db.repositories import accounts as account_repo
from finsca.db.repositories.accounts import AmbiguousAccountError, StatementProtectedError
from finsca.db.runtime import db_session

app = typer.Typer(help="List and manage bank accounts.")


def _parse_month(value: str) -> tuple[int, int]:
    try:
        year_s, month_s = value.split("-", 1)
        year, month = int(year_s), int(month_s)
    except ValueError as exc:
        raise typer.BadParameter("month must be YYYY-MM") from exc
    if month < 1 or month > 12:
        raise typer.BadParameter("month must be YYYY-MM")
    return year, month


def _account_id(account: Account) -> str:
    if not account.id:
        raise RuntimeError("account is missing id")
    return account.id


def _require_account(session: Session, token: str) -> Account:
    try:
        account = account_repo.resolve(session, token)
    except AmbiguousAccountError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    if account is None:
        console.print(f"[red]account not found: {token}[/red]")
        raise typer.Exit(code=1)
    return account


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_accounts()


@app.command("list")
def list_accounts() -> None:
    with db_session() as session:
        rows = account_repo.list_all(session)
    if not rows:
        console.print("no accounts yet")
        return
    table = Table(title="Accounts")
    table.add_column("id")
    table.add_column("name")
    table.add_column("type")
    table.add_column("institution")
    table.add_column("last4")
    table.add_column("aliases")
    for account in rows:
        table.add_row(
            (account.id or "")[:8],
            account.display_name,
            account.type.value,
            account.institution or "",
            account.last4 or "",
            ", ".join(account.holder_aliases),
        )
    console.print(table)


@app.command("add")
def add_account(
    name: str = typer.Argument(..., help="Display name"),
    account_type: AccountType = typer.Option(AccountType.SAVINGS, "--type"),
    institution: str | None = typer.Option(None, "--institution"),
    last4: str | None = typer.Option(None, "--last4"),
    alias: list[str] | None = typer.Option(None, "--alias"),
    upi: list[str] | None = typer.Option(None, "--upi"),
    credit_limit: str | None = typer.Option(None, "--credit-limit"),
) -> None:
    payload = Account(
        display_name=name,
        type=account_type,
        institution=institution,
        last4=last4,
        holder_aliases=alias or [],
        upi_vpas=upi or [],
        credit_limit=parse_inr(credit_limit) if credit_limit is not None else None,
    )
    with db_session() as session:
        account = account_repo.add(session, payload)
    console.print(
        f"added  {account.display_name}  id={(account.id or '')[:8]}  last4={account.last4 or '-'}"
    )


@app.command("alias")
def alias_account(
    account: str = typer.Argument(..., help="id prefix, last4, name, or existing alias"),
    alias: str = typer.Argument(..., help="Alias used for self-transfer matching"),
) -> None:
    with db_session() as session:
        found = _require_account(session, account)
        updated = account_repo.add_alias(session, _account_id(found), alias)
    console.print(f"alias  {updated.display_name}: {', '.join(updated.holder_aliases)}")


@app.command("rename")
def rename_account(
    account: str = typer.Argument(...),
    name: str = typer.Argument(...),
) -> None:
    with db_session() as session:
        found = _require_account(session, account)
        try:
            updated = account_repo.rename(session, _account_id(found), name)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
    console.print(f"renamed  {found.display_name} → {updated.display_name}")


@app.command("months")
def show_months(
    account: str | None = typer.Option(None, "--account", help="id prefix, last4, name, or alias"),
    month: str | None = typer.Option(None, "--month", help="YYYY-MM"),
) -> None:
    year = month_n = None
    if month:
        year, month_n = _parse_month(month)
    with db_session() as session:
        account_id = _account_id(_require_account(session, account)) if account else None
        rows = account_repo.list_months(session, account_id=account_id, year=year, month=month_n)
        names = {item.id: item.display_name for item in account_repo.list_all(session)}
    if not rows:
        console.print("no account months yet")
        return
    table = Table(title="Account months")
    table.add_column("account")
    table.add_column("month")
    table.add_column("opening", justify="right")
    table.add_column("closing", justify="right")
    table.add_column("source")
    for row in rows:
        table.add_row(
            names.get(row.account_id, (row.account_id or "")[:8]),
            f"{row.year:04d}-{row.month:02d}",
            format_inr(row.opening),
            format_inr(row.closing),
            row.source.value,
        )
    console.print(table)


@app.command("set-month")
def set_month(
    account: str = typer.Argument(...),
    month: str = typer.Option(..., "--month", help="YYYY-MM"),
    opening: str = typer.Option(..., "--opening"),
    closing: str = typer.Option(..., "--closing"),
    source: MonthSource = typer.Option(MonthSource.COMPUTED, "--source"),
) -> None:
    year, month_n = _parse_month(month)
    with db_session() as session:
        found = _require_account(session, account)
        try:
            stored = account_repo.set_month(
                session,
                AccountMonth(
                    account_id=_account_id(found),
                    year=year,
                    month=month_n,
                    opening=parse_inr(opening),
                    closing=parse_inr(closing),
                    source=source,
                ),
            )
        except StatementProtectedError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
    console.print(
        f"{found.display_name}  {stored.year:04d}-{stored.month:02d}  "
        f"open={format_inr(stored.opening)}  close={format_inr(stored.closing)}  "
        f"({stored.source.value})"
    )
