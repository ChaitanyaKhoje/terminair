"""SLA Miss Tracker screen - DAGs exceeding expected duration."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class SlaMissScreen(Screen):
    """Shows currently running DAGs that have exceeded their P95 duration."""

    CSS = """
    SlaMissScreen {
        layout: vertical;
    }

    #sla-table {
        height: 1fr;
    }

    #sla-summary {
        height: 3;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="sla-table")
        yield Static("", id="sla-summary")

    def on_mount(self) -> None:
        table = self.query_one("#sla-table")
        table.add_columns(
            "DAG ID",
            "Run ID",
            "State",
            "Running For",
            "P95 Duration",
            "Over By",
            "Started",
        )

    def update_sla(self, breaches: list, total_running: int):
        table = self.query_one("#sla-table")
        table.clear()

        if not breaches:
            self.query_one("#sla-summary").update(
                f"[green]Monitoring {total_running} running DAG run(s). No SLA breaches.[/green]"
            )
            return

        for b in breaches:
            over_by = b["over_by"]
            if over_by > 600:
                over_color = "red"
            elif over_by > 180:
                over_color = "yellow"
            else:
                over_color = "white"
            table.add_row(
                f"[cyan]{b['dag_id']}[/cyan]",
                b["run_id"][:30],
                f"[yellow]{b['state']}[/yellow]",
                _fmt_secs(b["running_for"]),
                f"[dim]{_fmt_secs(b['p95'])}[/dim]",
                f"[{over_color}]+{_fmt_secs(over_by)}[/{over_color}]",
                b["started"][:16],
            )

        self.query_one("#sla-summary").update(
            f"[bold red]{len(breaches)} SLA breach(es)[/bold red] "
            f"[dim]out of {total_running} running run(s)[/dim]"
        )


def _fmt_secs(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    return f"{int(secs // 60)}m {int(secs % 60)}s"
