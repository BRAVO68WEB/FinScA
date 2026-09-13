from __future__ import annotations

import typer

from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.ingest.email import gmail_api

app = typer.Typer(help="Pull bank-alert mail via the Gmail API (readonly).")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("finsca gmail login")
        console.print("finsca gmail pull [--months 6] [--query ...] [--max 200]")


@app.command("login")
def login_cmd() -> None:
    settings = Settings()
    settings.ensure_dirs()
    try:
        dest = gmail_api.login(settings)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except ImportError as exc:
        console.print("[red]Gmail extra not installed. pip install -e '.[gmail]'[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"logged in  token={dest}")


@app.command("pull")
def pull_cmd(
    months: int | None = typer.Option(None, "--months", min=1, help="How many months back (Gmail newer_than:Nm)"),
    query: str | None = typer.Option(None, "--query", help="Gmail search query (time window added unless already set)"),
    max_results: int = typer.Option(200, "--max"),
) -> None:
    settings = Settings()
    settings.ensure_dirs()
    window = months if months is not None else settings.gmail_months
    try:
        built = gmail_api.search_query(months=window, extra=query or settings.gmail_query)
        result = gmail_api.pull(settings, query=query, months=window, max_results=max_results)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except ImportError as exc:
        console.print("[red]Gmail extra not installed. pip install -e '.[gmail]'[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"query   {built}")
    console.print(f"pulled  emails={result.emails}  pdfs={result.pdfs}  → {settings.inbox_dir}")
    console.print("run  finsca ingest")
