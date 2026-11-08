from __future__ import annotations

import typer

from finsca.agents.orchestrator import answer_question
from finsca.cli.render import console
from finsca.config.settings import Settings
from finsca.db.runtime import db_session

app = typer.Typer(help="Ask the ledger a question.")


@app.callback(invoke_without_command=True)
def ask(
    question: str = typer.Argument(..., help="Question about the ledger"),
) -> None:
    settings = Settings()
    with db_session() as session:
        console.print(answer_question(session, settings, question))
