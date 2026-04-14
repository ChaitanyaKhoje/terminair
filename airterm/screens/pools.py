"""Pools screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class PoolsScreen(Screen):
    CSS = """
    PoolsScreen {
        layout: grid;
        grid-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="pools-table")
        e = Static("No pools found", id="pools-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#pools-table")
        table.add_columns(
            "Pool Name",
            "Slots Used",
            "Slots Queued",
            "Slots Total",
            "Utilization",
            "Running",
        )

    def update_pools(self, pools: list):
        table = self.query_one("#pools-table")
        table.clear()
        empty = self.query_one("#pools-empty")
        if not pools:
            empty.show()
            return
        empty.hide()
        for pool in pools:
            util = 0
            if pool.slots > 0:
                util = (pool.used_slots / pool.slots) * 100
            bar = "█" * int(util / 10) + "░" * (10 - int(util / 10))
            table.add_row(
                pool.name,
                str(pool.used_slots),
                str(pool.queued_slots),
                str(pool.slots),
                f"{util:.0f}% {bar}",
                str(pool.running_slots),
            )
