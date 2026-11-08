"""plotext bars for the CLI. Missing plotext falls back to Rich."""

from __future__ import annotations

from collections.abc import Sequence


def plot_bars(title: str, rows: Sequence[tuple[str, object]]) -> str | None:
    if not rows:
        return None
    try:
        import plotext as plt
    except ImportError:
        return None
    plt.clear_figure()
    plt.bar([str(name) for name, _ in rows], [float(amount) for _, amount in rows])
    plt.title(title)
    return plt.build()
