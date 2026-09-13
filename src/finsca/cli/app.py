from __future__ import annotations

import typer

from finsca.cli.commands import accounts, ask, config_cmd, ingest, label, loans, report, review
from finsca.cli.status import print_status

app = typer.Typer(
    name="finsca",
    help="Financial Services Agent — local ledger and monthly report CLI.",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show ledger status when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        print_status()


app.add_typer(ingest.app, name="ingest")
app.add_typer(review.app, name="review")
app.add_typer(label.app, name="label")
app.add_typer(accounts.app, name="accounts")
app.add_typer(loans.app, name="loans")
app.add_typer(report.app, name="report")
app.add_typer(ask.app, name="ask")
app.add_typer(config_cmd.app, name="config")
