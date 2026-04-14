"""Status bar widget."""

from __future__ import annotations

from typing import Optional

from textual.widgets import Static


class StatusBar(Static):
    def __init__(self):
        super().__init__("")

    def update_status(
        self,
        connection: str = "n/a",
        latency_ms: float = 0.0,
        loading: bool = False,
        error: Optional[str] = None,
    ):
        parts = []
        if error:
            parts.append(f"[red]{error}[/red]")
        else:
            parts.append(f"Context: [cyan]{connection}[/cyan]")
        if latency_ms > 0:
            parts.append(f"Latency: {latency_ms:.0f}ms")
        if loading:
            parts.append("[yellow]loading...[/yellow]")
        self.update("  ".join(parts))
