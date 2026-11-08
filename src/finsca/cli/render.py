"""Shared Rich tables. Commands keep their own column text."""

from __future__ import annotations

from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from finsca.core.money import format_inr, parse_inr

console = Console()


def money_table(
    title: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[object]],
    *,
    right: set[str] | None = None,
) -> None:
    table = Table(title=title)
    aligned = right or set()
    for name in columns:
        if name in aligned:
            table.add_column(name, justify="right")
        else:
            table.add_column(name)
    for row in rows:
        table.add_row(*["" if cell is None else str(cell) for cell in row])
    console.print(table)


def bars(title: str, rows: Sequence[tuple[str, object]]) -> None:
    if not rows:
        console.print(f"{title}  (none)")
        return
    table = Table(title=title)
    table.add_column("name")
    table.add_column("amount", justify="right")
    table.add_column("bar")
    peak = max((float(amount) for _, amount in rows), default=0) or 1
    for name, amount in rows:
        width = int(20 * float(amount) / peak)
        table.add_row(str(name), format_inr(parse_inr(amount)), "█" * width)
    console.print(table)
