"""DAG Detail screen with run history and metrics panel."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class DagDetailScreen(Screen):
    CSS = """
    DagDetailScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 12;
    }

    #run-table {
        height: 100%;
    }

    #metrics-panel {
        height: 100%;
        background: $panel;
        padding: 1 2;
    }

    .metric-label {
        color: $text-muted;
    }

    .metric-value {
        color: $text;
    }

    .sparkline {
        color: $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="run-table")
        yield Static("", id="metrics-panel")

    def on_mount(self) -> None:
        table = self.query_one("#run-table")
        table.add_columns(
            "Run ID",
            "State",
            "Type",
            "Execution",
            "Duration",
            "vs Avg",
            "Error",
        )

    def update_runs(self, runs: list, avg_duration: float = 0.0):
        table = self.query_one("#run-table")
        table.clear()
        for run in runs:
            duration = ""
            vs_avg = ""
            if run.start_date and run.end_date:
                delta = run.end_date - run.start_date
                seconds = delta.total_seconds()
                duration = f"{int(seconds // 60)}m {int(seconds % 60)}s"
                if avg_duration > 0:
                    drift = ((seconds - avg_duration) / avg_duration) * 100
                    sign = "+" if drift > 0 else ""
                    vs_avg = f"{sign}{drift:.0f}%"

            error = ""
            if run.state.value == "failed":
                error = run.dag_run_id[:30]

            table.add_row(
                run.dag_run_id[:30],
                run.state.value if run.state else "",
                run.run_type,
                str(run.execution_date)[:16],
                duration,
                vs_avg,
                error,
            )

    def update_metrics(
        self,
        dag_id: str,
        schedule: str,
        owner: str,
        total_runs: int,
        success_count: int,
        failure_count: int,
        success_rate: float,
        avg_duration: float,
        p95_duration: float,
        streak_type: str,
        streak_count: int,
        sparkline: str,
        last_failure: str,
    ):
        self.query_one("#metrics-panel").update(
            f"""DAG: {dag_id} | Schedule: {schedule} | Owner: {owner}
─────────────────────────────────────────────
Runs (last 30d): {total_runs} total | {success_count} success | {failure_count} failed
Success Rate:     {success_rate:.1f}%
Avg Duration:     {int(avg_duration // 60)}m {int(avg_duration % 60)}s
P95 Duration:    {int(p95_duration // 60)}m {int(p95_duration % 60)}s
Last Failure:     {last_failure or "none"}
Failure Streak:   {streak_count} ({streak_type})
Duration Trend: {sparkline}
"""
        )
