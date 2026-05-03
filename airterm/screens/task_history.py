"""Task History screen - cross run pass/fail pattern."""


from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class TaskHistoryScreen(Screen):
    CSS = """
    TaskHistoryScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 4;
    }

    #history-table {
        height: 100%;
    }

    #summary-panel {
        height: 100%;
        background: $panel;
        padding: 1 2;
    }
    """

    def __init__(self):
        super().__init__()
        self._current_task_id: str | None = None
        self._current_dag_id: str | None = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="history-table")
        yield Static("", id="summary-panel")

    def on_mount(self) -> None:
        table = self.query_one("#history-table")
        table.add_columns(
            "Run",
            "State",
            "Duration",
            "Try",
        )

    def set_context(self, task_id: str, dag_id: str):
        self._current_task_id = task_id
        self._current_dag_id = dag_id

    def update_history(
        self,
        entries: list,
        failure_rate: float,
        avg_duration: float,
        avg_retries: float,
        pattern: str,
    ):
        table = self.query_one("#history-table")
        table.clear()

        for entry in entries:
            duration = f"{entry.get('duration', 0):.1f}s" if entry.get("duration") else ""
            table.add_row(
                entry.get("run_id", "")[:30],
                entry.get("state", ""),
                duration,
                entry.get("try_number", ""),
            )

        self.query_one("#summary-panel").update(
            f"""Task: {self._current_task_id} | DAG: {self._current_dag_id}
─────────────────────────────────────────
Pattern: {pattern}
Failure Rate: {failure_rate:.1f}%
Avg Duration: {avg_duration:.1f}s
Retries per Run: {avg_retries:.1f} avg
"""
        )
