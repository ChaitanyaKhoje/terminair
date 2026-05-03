"""Pools screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static

from airterm.logging_utils import get_logger

_logger = get_logger("airterm.pools")


class PoolsScreen(Screen):
    CSS = """
    PoolsScreen {
        layout: vertical;
    }

    #pools-table {
        height: 1fr;
    }

    #pools-alert {
        height: 3;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="pools-table")
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
        try:
            _logger.debug(
                f"PoolsScreen.update_pools called; pools_count={len(pools) if pools is not None else 0}"
            )
        except Exception:
            pass

        table = self.query_one("#pools-table")
        table.clear()
        if not pools:
            self.query_one("#pools-alert").update("[dim]No pools found[/dim]")
            return

        starved = []
        for pool in pools:
            util = 0.0
            if pool.slots > 0:
                util = (pool.used_slots / pool.slots) * 100
                filled = int(util / 10)
                bar_raw = "█" * filled + "░" * (10 - filled)
                if util < 60:
                    bar = f"[green]{bar_raw}[/green]"
                elif util < 85:
                    bar = f"[yellow]{bar_raw}[/yellow]"
                else:
                    bar = f"[red]{bar_raw}[/red]"
            else:
                bar = "[dim]░░░░░░░░░░[/dim]"

            # Contention: pool is at capacity and tasks are waiting
            at_capacity = pool.slots > 0 and pool.open_slots == 0
            contention = ""
            if at_capacity and pool.queued_slots > 0:
                contention = f"[red]⚠ {pool.queued_slots} waiting[/red]"
                starved.append((pool.name, pool.queued_slots))
            elif at_capacity:
                contention = "[yellow]full[/yellow]"

            util_color = "green" if util < 60 else ("yellow" if util < 85 else "red")
            table.add_row(
                pool.name,
                str(pool.used_slots),
                f"[cyan]{pool.queued_slots}[/cyan]" if pool.queued_slots else "0",
                str(pool.running_slots),
                str(pool.open_slots),
                str(pool.slots),
                f"[{util_color}]{util:.0f}%[/{util_color}] {bar}",
                contention,
            )

        if starved:
            msgs = ", ".join(f"[yellow]{name}[/yellow] ({n} tasks queued)" for name, n in starved)
            self.query_one("#pools-alert").update(f"[bold red]Pool Starvation:[/bold red] {msgs}")
        else:
            self.query_one("#pools-alert").update("[green]All pools have capacity.[/green]")
        try:
            _logger.debug("PoolsScreen.update_pools finished updating widgets")
        except Exception:
            pass
