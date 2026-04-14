"""SLA Miss Tracker screen - DAGs exceeding expected duration."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class SlaMissScreen(Screen):
    """Shows currently running DAGs that have exceeded their P95 duration."""

    CSS = """
    SlaMissScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 4;
    }

    #sla-table {
        height: 100%;
    }

    #sla-summary {
        height: 100%;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="sla-table")
        e = Static("No SLA breaches detected.", id="sla-empty")
        e.display = False
        yield e
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
        empty = self.query_one("#sla-empty")

        if not breaches:
            empty.display = True
            self.query_one("#sla-summary").update(
                f"Monitoring {total_running} running DAG run(s). No SLA breaches."
            )
            return

        empty.display = False
        for b in breaches:
            table.add_row(
                b["dag_id"],
                b["run_id"][:30],
                b["state"],
                _fmt_secs(b["running_for"]),
                _fmt_secs(b["p95"]),
                f"+{_fmt_secs(b['over_by'])}",
                b["started"][:16],
            )

        self.query_one("#sla-summary").update(
            f"[bold red]{len(breaches)} SLA breach(es)[/bold red] out of {total_running} running run(s)."
        )


def _fmt_secs(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    return f"{int(secs // 60)}m {int(secs % 60)}s"
