"""Recent Activity screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class RecentActivityScreen(Screen):
    CSS = """
    RecentActivityScreen {
        layout: grid;
        grid-size: 1 1;
    }

    .state-failed { color: $error; }
    .state-success { color: $success; }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="activity-table")
        e = Static("No recent activity", id="activity-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#activity-table")
        table.add_columns(
            "Time",
            "DAG ID",
            "Run ID",
            "State",
            "Duration",
            "Failed Task",
        )

    def update_activity(self, runs: list):
        table = self.query_one("#activity-table")
        table.clear()
        empty = self.query_one("#activity-empty")
        if not runs:
            empty.show()
            return
        empty.hide()

        for run in runs:
            duration = ""
            if run.start_date and run.end_date:
                delta = run.end_date - run.start_date
                duration = f"{int(delta.total_seconds())}s"

            time_str = str(run.end_date)[:19] if run.end_date else ""
            failed_task = "N/A"

            table.add_row(
                time_str,
                run.dag_id,
                run.dag_run_id[:30],
                run.state.value if run.state else "",
                duration,
                failed_task,
            )
