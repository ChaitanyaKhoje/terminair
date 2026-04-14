"""Task Instances screen - shows tasks with error summary column."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static


class TaskInstancesScreen(Screen):
    CSS = """
    TaskInstancesScreen {
        layout: grid;
        grid-size: 1 1;
    }

    TaskInstancesScreen.log-visible {
        grid-size: 1 2;
        grid-rows: 1fr 12;
    }

    #log-panel {
        display: none;
        height: 100%;
        background: $panel;
        padding: 0 2;
        overflow-y: auto;
    }

    TaskInstancesScreen.log-visible #log-panel {
        display: block;
    }

    .state-failed { color: $error; }
    .state-success { color: $success; }
    .state-running { color: $warning; }
    .state-queued { color: $info; }
    """

    BINDINGS = [
        Binding("l", "toggle_log", "Log"),
    ]

    def __init__(self):
        super().__init__()
        self._current_dag_id: Optional[str] = None
        self._current_run_id: Optional[str] = None
        self._log_visible = False

    def compose(self) -> ComposeResult:
        yield DataTable(id="task-instances-table")
        e = Static("No tasks found", id="tasks-empty")
        e.display = False
        yield e
        yield Static("Press l on a task to view log snippet", id="log-panel")

    def on_mount(self) -> None:
        table = self.query_one("#task-instances-table")
        table.add_columns(
            "Task ID",
            "State",
            "Operator",
            "Start",
            "Queue Latency",
            "Duration",
            "Try",
            "Pool",
            "SLA",
        )

    def set_context(self, dag_id: str, run_id: str):
        self._current_dag_id = dag_id
        self._current_run_id = run_id

    def get_context(self) -> tuple:
        return self._current_dag_id, self._current_run_id

    def update_tasks(self, tasks: list):
        table = self.query_one("#task-instances-table")
        table.clear()
        empty = self.query_one("#tasks-empty")
        if not tasks:
            empty.show()
            return
        empty.hide()

        sorted_tasks = self._sort_by_state_first(tasks)
        for task in sorted_tasks:
            duration = f"{task.duration:.1f}s" if task.duration else "running"
            trys = f"{task.try_number}/{task.max_tries}"
            sla = "⚠ SLA" if task.sla_miss else ""
            queue_latency = ""
            if task.queued_when and task.start_date:
                ql_secs = (task.start_date - task.queued_when).total_seconds()
                if ql_secs >= 0:
                    queue_latency = f"{ql_secs:.0f}s"
            table.add_row(
                task.task_id,
                task.state.value if task.state else "",
                task.operator,
                str(task.start_date)[:19] if task.start_date else "",
                queue_latency,
                duration,
                trys,
                task.pool,
                sla,
            )

    def action_toggle_log(self):
        """Toggle log panel visibility and request log for selected task."""
        if self._log_visible:
            self._log_visible = False
            self.remove_class("log-visible")
            return

        table = self.query_one("#task-instances-table")
        if table.cursor_row is None:
            return

        try:
            row = table.get_row_at(table.cursor_row)
            task_id = row[0]
            try_number = 1
            try_str = row[6]  # "try/max"
            if "/" in str(try_str):
                try_number = int(str(try_str).split("/")[0])
        except Exception:
            return

        self._log_visible = True
        self.add_class("log-visible")
        self.query_one("#log-panel").update(f"Loading log for {task_id}...")

        # Trigger log load via app
        from textual.app import asyncio
        asyncio.create_task(
            self.app._load_task_log(
                self._current_dag_id, self._current_run_id, task_id, try_number
            )
        )

    def update_log(self, task_id: str, log_text: str):
        """Update the log panel with log content."""
        self.query_one("#log-panel").update(
            f"[bold]Log: {task_id}[/bold] (last 30 lines)\n"
            f"──────────────────────────────────────\n"
            f"{log_text}"
        )

    def _sort_by_state_first(self, tasks: list) -> list:
        priority = {"failed": 0, "running": 1, "queued": 2, "up_for_retry": 3}

        def sort_key(task):
            state = task.state.value if task.state else "unknown"
            return priority.get(state, 99)

        return sorted(tasks, key=sort_key)
