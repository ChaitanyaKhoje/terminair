"""Resource Timeline screen - pool slot usage over the last 24 hours."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static
import logging
import os


# Ensure a simple file-based logger is available for TUI-debugging. We avoid
# configuring root logger to prevent surprising global effects; instead use a
# module-level logger that appends to /tmp/airterm-debug.log so logs are
# visible even if stdout/stderr are swallowed by the TUI.
_LOG_PATH = "/tmp/airterm-debug.log"
_logger = logging.getLogger("airterm.resource_timeline")
if not _logger.handlers:
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    except Exception:
        pass
    fh = logging.FileHandler(_LOG_PATH, mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(fh)
    _logger.setLevel(logging.DEBUG)


class ResourceTimelineScreen(Screen):
    """Horizontal timeline of pool slot usage by DAG over 24 hours."""

    CSS = """
    ResourceTimelineScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 10;
    }

    #timeline-grid {
        height: 100%;
        padding: 1 2;
        overflow-y: auto;
    }

    #timeline-consumers {
        height: 100%;
        background: $panel;
        padding: 0 2;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Loading timeline...", id="timeline-grid")
        yield Static("", id="timeline-consumers")

    def update_timeline(
        self, pool_hours: dict, pool_capacity: dict, top_consumers: list, error: str = ""
    ):
        """
        pool_hours: {pool_name: {hour_offset: slot_count, ...}, ...}
            hour_offset 0 = now, 23 = 23 hours ago
        pool_capacity: {pool_name: total_slots}
        top_consumers: [{"dag_id": str, "slot_minutes": float, "pool": str}, ...]
        """
        # Debug print to help trace why timeline might not update in some envs
        try:
            msg = f"ResourceTimelineScreen.update_timeline called; pools={len(pool_hours)} consumers={len(top_consumers)} error={'yes' if error else 'no'}"
            print("DEBUG:", msg)
            _logger.debug(msg)
        except Exception:
            # prints can fail in some TUI environments; ignore failures
            pass

        if error:
            self.query_one("#timeline-grid").update(
                f"[red]Failed to load timeline:[/red]\n\n{error}"
            )
            self.query_one("#timeline-consumers").update("")
            return

        shades = " ░▒▓█"
        lines = []

        # Header with hour labels (right = now, left = 24h ago)
        hour_labels = "".join(f"{(23 - h):02d}" if h % 4 == 0 else "  " for h in range(24))
        lines.append(f"{'Pool':<20} {hour_labels}  Cap")
        lines.append("─" * 75)

        if not pool_hours:
            lines.append("No activity in the last 24 hours.")
        else:
            for pool_name in sorted(pool_hours.keys()):
                hours = pool_hours[pool_name]
                capacity = pool_capacity.get(pool_name, 1)
                row = f"{pool_name:<20} "
                for h in range(24):
                    # h=0 is 23h ago, h=23 is now
                    slot_count = hours.get(23 - h, 0)
                    if capacity > 0:
                        ratio = min(slot_count / capacity, 1.0)
                        idx = min(int(ratio * 4), 4)
                    else:
                        idx = 0
                    row += shades[idx] * 2
                row += f"  {capacity}"
                lines.append(row)

        lines.append("")
        lines.append("← 23h ago" + " " * 28 + "now →")

        self.query_one("#timeline-grid").update("\n".join(lines))

        # Top consumers panel
        if top_consumers:
            consumer_lines = [
                "[bold]Top Consumers (last 24h)[/bold]",
                "──────────────────────────────────────",
            ]
            for c in top_consumers[:10]:
                slot_hrs = c["slot_minutes"] / 60
                consumer_lines.append(
                    f"  {c['dag_id']:<30} {slot_hrs:>6.1f} slot-hrs  ({c['pool']})"
                )
            self.query_one("#timeline-consumers").update("\n".join(consumer_lines))
        else:
            self.query_one("#timeline-consumers").update("No task activity in the last 24 hours.")
