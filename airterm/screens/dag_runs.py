"""DAG Runs screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class DagRunsScreen(Screen):
    CSS = """
    DagRunsScreen {
        layout: grid;
        grid-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="dag-runs-table")
        e = Static("No runs found", id="runs-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#dag-runs-table")
        table.add_columns(
            "Run ID",
            "State",
            "Type",
            "Execution Date",
            "Start",
            "End",
            "Duration",
            "External",
        )

    def update_runs(self, runs: list):
        table = self.query_one("#dag-runs-table")
        table.clear()
        empty = self.query_one("#runs-empty")
        if not runs:
            empty.show()
            return
        empty.hide()
        for run in runs:
            duration = ""
            if run.start_date and run.end_date:
                duration = str(run.end_date - run.start_date)
            table.add_row(
                run.dag_run_id,
                run.state.value if run.state else "",
                run.run_type,
                str(run.execution_date) if run.execution_date else "",
                str(run.start_date) if run.start_date else "",
                str(run.end_date) if run.end_date else "",
                duration,
                "yes" if run.external_trigger else "no",
            )
