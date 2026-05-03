"""Health screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class HealthScreen(Screen):
    CSS = """
    HealthScreen {
        layout: vertical;
        padding: 1 2;
    }

    #health-panel {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="health-panel")

    def update_health(self, health):
        if not health:
            return
        sched = health.scheduler
        metadb = health.metadatabase
        sched_color = "green" if sched.status == "healthy" else "red"
        metadb_color = "green" if metadb.status == "healthy" else "red"
        heartbeat = sched.latest_scheduler_heartbeat or "n/a"
        self.query_one("#health-panel").update(
            f"SCHEDULER\n"
            f"  Status:     [{sched_color}]{sched.status}[/{sched_color}]\n"
            f"  Last beat:  [dim]{str(heartbeat)[:19]}[/dim]\n"
            f"\n"
            f"METADATABASE\n"
            f"  Status:     [{metadb_color}]{metadb.status}[/{metadb_color}]"
        )
