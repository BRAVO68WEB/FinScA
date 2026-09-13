from __future__ import annotations

import typer


def stub_app(help_text: str, phase: str) -> typer.Typer:
    app = typer.Typer(help=help_text)

    @app.callback(invoke_without_command=True)
    def _not_ready(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            typer.echo(f"{ctx.info_name} is not implemented yet ({phase})")

    return app
