"""Watchlist screen - bookmarked DAGs with status summary."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class WatchlistScreen(Screen):
    """Shows only bookmarked DAGs with their latest status."""

    CSS = """
    WatchlistScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 3;
    }

    #watchlist-table {
        height: 100%;
    }

    #watchlist-summary {
        height: 100%;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="watchlist-table")
        e = Static("No bookmarked DAGs. Press b on DAGs screen to bookmark.", id="watchlist-empty")
        e.display = False
        yield e
        yield Static("", id="watchlist-summary")

    def on_mount(self) -> None:
        table = self.query_one("#watchlist-table")
        table.add_columns(
            "DAG ID",
            "State",
            "Last Run",
            "Duration",
            "Avg Duration",
            "Drift",
            "Success Rate",
        )

    def update_watchlist(self, entries: list):
        """
        entries: list of dicts with keys:
            dag_id, state, last_run, duration, avg_duration, drift, success_rate
        """
        table = self.query_one("#watchlist-table")
        table.clear()
        empty = self.query_one("#watchlist-empty")

        if not entries:
            empty.display = True
            self.query_one("#watchlist-summary").update(
                "Press [bold]b[/bold] on the DAGs screen to bookmark DAGs."
            )
            return

        empty.display = False
        healthy = 0
        for e in entries:
            drift_str = e.get("drift", "")
            table.add_row(
                e["dag_id"],
                e.get("state", ""),
                e.get("last_run", ""),
                e.get("duration", ""),
                e.get("avg_duration", ""),
                drift_str,
                e.get("success_rate", ""),
            )
            if e.get("state") == "success":
                healthy += 1

        self.query_one("#watchlist-summary").update(
            f"Watching {len(entries)} DAG(s) | "
            f"{healthy} healthy | "
            f"{len(entries) - healthy} need attention"
        )
