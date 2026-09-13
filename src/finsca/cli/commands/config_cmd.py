from __future__ import annotations

import typer

from finsca.cli.render import console
from finsca.config.settings import Settings

app = typer.Typer(help="Show current FinScA configuration.")


@app.callback(invoke_without_command=True)
def show() -> None:
    settings = Settings()
    console.print("[bold]FinScA config[/bold]")
    console.print(f"data_dir              {settings.data_dir}")
    console.print(f"db_path               {settings.db_path}")
    console.print(f"reasoning_provider    {settings.reasoning_provider}")
    console.print(f"compact_provider      {settings.compact_provider}")
    console.print(f"grok_model            {settings.grok_model}")
    console.print(f"openai_model          {settings.openai_model}")
    console.print(f"compact_model         {settings.compact_model}")
    console.print(f"label_min_confidence  {settings.label_min_confidence}")
    console.print(f"self_transfer_window  {settings.self_transfer_window_hours}h")
    console.print(f"llm_off               {settings.llm_off}")
