"""Event Log screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class EventLogScreen(Screen):
    CSS = """
    EventLogScreen {
        layout: grid;
        grid-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="event-log-table")
        e = Static("No events", id="events-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#event-log-table")
        table.add_columns("Timestamp", "Type", "Task", "DAG", "Run", "Owner")

    def update_events(self, events: list):
        table = self.query_one("#event-log-table")
        table.clear()
        empty = self.query_one("#events-empty")
        if not events:
            empty.show()
            return
        empty.hide()
        for ev in events:
            table.add_row(
                str(ev.event_timestamp) if ev.event_timestamp else "",
                ev.event_type,
                ev.task_id or "",
                ev.dag_id or "",
                ev.run_id or "",
                ev.owner or "",
            )
