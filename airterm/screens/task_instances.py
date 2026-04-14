"""Task Instances screen - shows tasks with error summary column."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class TaskInstancesScreen(Screen):
    CSS = """
    TaskInstancesScreen {
        layout: grid;
        grid-size: 1 1;
    }

    .state-failed { color: $error; }
    .state-success { color: $success; }
    .state-running { color: $warning; }
    .state-queued { color: $info; }
    """

    def __init__(self):
        super().__init__()
        self._current_dag_id: Optional[str] = None
        self._current_run_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="task-instances-table")
        e = Static("No tasks found", id="tasks-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#task-instances-table")
        table.add_columns(
            "Task ID",
            "State",
            "Operator",
            "Start",
            "Duration",
            "Try",
            "Pool",
            "Error",
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
            error = task.state.value if task.state == "failed" else ""
            table.add_row(
                task.task_id,
                task.state.value if task.state else "",
                task.operator,
                str(task.start_date)[:19] if task.start_date else "",
                duration,
                trys,
                task.pool,
                error,
            )

    def _sort_by_state_first(self, tasks: list) -> list:
        priority = {"failed": 0, "running": 1, "queued": 2, "up_for_retry": 3}

        def sort_key(task):
            state = task.state.value if task.state else "unknown"
            return priority.get(state, 99)

        return sorted(tasks, key=sort_key)
