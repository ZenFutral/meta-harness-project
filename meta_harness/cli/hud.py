# Rich terminal HUD for Meta-Harness.

"""Provides a minimal helper `_make_dashboard` used by the test suite to verify
that the Rich components can be constructed without a live terminal. The
function returns a :class:`rich.panel.Panel` containing a simple table of the
provided metrics and a descriptive title.
"""

from __future__ import annotations

from typing import Mapping, Any

from rich.panel import Panel
from rich.table import Table

def _make_dashboard(metrics: Mapping[str, Any]) -> Panel:
    """Create a Rich ``Panel`` displaying ``metrics``.

    The implementation is deliberately lightweight – it constructs a ``Table``
    with two columns (key and value) and wraps it in a ``Panel`` whose title is
    "Meta‑Harness HUD".
    """
    table = Table.grid(padding=(0, 1))
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="magenta")
    for key, value in metrics.items():
        table.add_row(str(key), str(value))
    return Panel(table, title="Meta-Harness HUD")


def main() -> None:
    """Display the Rich terminal HUD."""
    from rich.console import Console
    console = Console()
    sample_metrics = {
        "Status": "Active",
        "Repomap SQLite-WAL": "Ready",
        "SWE Orchestrator": "6 Personas Active",
        "Router": "Dual-Engine Dual-Provider",
    }
    console.print(_make_dashboard(sample_metrics))


if __name__ == "__main__":
    main()

