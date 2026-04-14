"""XCom Viewer screen - read-only peek at XCom keys and values."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class XComViewerScreen(Screen):
    CSS = """
    XComViewerScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 8;
    }

    #xcom-table {
        height: 100%;
    }

    #xcom-value-panel {
        height: 100%;
        background: $panel;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    def __init__(self):
        super().__init__()
        self._dag_id: Optional[str] = None
        self._run_id: Optional[str] = None
        self._task_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="xcom-table")
        yield Static("Select a row to preview value", id="xcom-value-panel")

    def on_mount(self) -> None:
        table = self.query_one("#xcom-table")
        table.add_columns("Key", "Task ID", "Timestamp", "Value Preview")

    def set_context(self, dag_id: str, run_id: str, task_id: str):
        self._dag_id = dag_id
        self._run_id = run_id
        self._task_id = task_id

    def get_context(self) -> tuple:
        return self._dag_id, self._run_id, self._task_id

    def update_xcoms(self, entries: list):
        table = self.query_one("#xcom-table")
        table.clear()
        if not entries:
            self.query_one("#xcom-value-panel").update(
                f"No XCom entries for task: {self._task_id}"
            )
            return

        for entry in entries:
            ts = str(entry.timestamp)[:19] if entry.timestamp else ""
            preview = (entry.value or "")[:60]
            if entry.value and len(entry.value) > 60:
                preview += "…"
            table.add_row(
                entry.key,
                entry.task_id,
                ts,
                preview,
            )

        self.query_one("#xcom-value-panel").update(
            f"DAG: {self._dag_id}  Run: {self._run_id}  Task: {self._task_id}\n"
            f"──────────────────────────────────────\n"
            f"{len(entries)} XCom key(s) found. Navigate rows to inspect."
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#xcom-table")
        try:
            row = table.get_row(event.row_key)
            key = row[0]
            value_preview = row[3]
            self.query_one("#xcom-value-panel").update(
                f"Key: {key}\n"
                f"──────────────────────────────────────\n"
                f"{value_preview}"
            )
        except Exception:
            pass
