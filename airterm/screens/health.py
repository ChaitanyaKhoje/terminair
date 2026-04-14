"""Health screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class HealthScreen(Screen):
    CSS = """
    HealthScreen {
        layout: grid;
        grid-size: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("SCHEDULER", id="scheduler-title")
        yield Static("", id="scheduler-status")
        yield Static("METADATABASE", id="metadb-title")
        yield Static("", id="metadb-status")

    def update_health(self, health):
        if not health:
            return
        sched = self.query_one("#scheduler-status")
        sched.update(health.scheduler.status)
        metadb = self.query_one("#metadb-status")
        metadb.update(health.metadatabase.status)
