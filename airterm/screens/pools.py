"""Pools screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class PoolsScreen(Screen):
    CSS = """
    PoolsScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 5;
    }

    #pools-table {
        height: 100%;
    }

    #pools-alert {
        height: 100%;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="pools-table")
        e = Static("No pools found", id="pools-empty")
        e.display = False
        yield e
        yield Static("", id="pools-alert")

    def on_mount(self) -> None:
        table = self.query_one("#pools-table")
        table.add_columns(
            "Pool Name",
            "Used",
            "Queued",
            "Running",
            "Open",
            "Total",
            "Utilization",
            "Contention",
        )

    def update_pools(self, pools: list):
        table = self.query_one("#pools-table")
        table.clear()
        empty = self.query_one("#pools-empty")
        if not pools:
            empty.show()
            self.query_one("#pools-alert").update("")
            return
        empty.hide()

        starved = []
        for pool in pools:
            util = 0
            if pool.slots > 0:
                util = (pool.used_slots / pool.slots) * 100
                bar = "█" * int(util / 10) + "░" * (10 - int(util / 10))
            else:
                bar = "░" * 10

            # Contention: pool is at capacity and tasks are waiting
            at_capacity = pool.slots > 0 and pool.open_slots == 0
            contention = ""
            if at_capacity and pool.queued_slots > 0:
                contention = f"⚠ {pool.queued_slots} waiting"
                starved.append((pool.name, pool.queued_slots))
            elif at_capacity:
                contention = "full"

            table.add_row(
                pool.name,
                str(pool.used_slots),
                str(pool.queued_slots),
                str(pool.running_slots),
                str(pool.open_slots),
                str(pool.slots),
                f"{util:.0f}% {bar}",
                contention,
            )

        if starved:
            msgs = ", ".join(f"{name} ({n} tasks queued)" for name, n in starved)
            self.query_one("#pools-alert").update(
                f"[bold red]Pool Starvation:[/bold red] {msgs}"
            )
        else:
            self.query_one("#pools-alert").update("All pools have capacity.")
