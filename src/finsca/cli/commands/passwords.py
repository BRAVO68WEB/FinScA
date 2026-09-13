from __future__ import annotations

import typer
from rich.table import Table

from finsca.cli.render import console
from finsca.config.passwords import add_password, load_store, mask, save_store, store_path
from finsca.config.settings import Settings

app = typer.Typer(help="Local store of PDF passwords for locked CC/bank statements.")


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_cmd()


@app.command("list")
def list_cmd() -> None:
    settings = Settings()
    entries = load_store(store_path(settings))
    if not entries:
        console.print(f"no passwords  —  {store_path(settings)}")
        console.print("finsca passwords add SECRET --match hdfc")
        return
    table = Table(title=str(store_path(settings)))
    table.add_column("#")
    table.add_column("match")
    table.add_column("password")
    for index, item in enumerate(entries, start=1):
        table.add_row(str(index), item.match or "*", mask(item.password))
    console.print(table)


@app.command("add")
def add_cmd(
    password: str = typer.Argument(..., help="PDF password (DOB ddmmyyyy, PAN, card PIN, …)"),
    match: str | None = typer.Option(None, "--match", help="Only try for filenames containing this"),
) -> None:
    settings = Settings()
    settings.ensure_dirs()
    add_password(password, match=match, path=store_path(settings))
    console.print(f"stored  {mask(password)}" + (f"  match={match}" if match else "  (all PDFs)"))


@app.command("remove")
def remove_cmd(index: int = typer.Argument(..., min=1, help="1-based index from finsca passwords list")) -> None:
    settings = Settings()
    dest = store_path(settings)
    entries = load_store(dest)
    if index > len(entries):
        console.print(f"[red]no entry #{index}[/red]")
        raise typer.Exit(code=1)
    gone = entries.pop(index - 1)
    save_store(entries, dest)
    console.print(f"removed  {mask(gone.password)}" + (f"  match={gone.match}" if gone.match else ""))
