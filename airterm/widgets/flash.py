"""Flash message widget — k9s-inspired status feedback."""

from enum import Enum
from dataclasses import dataclass, field
from time import monotonic

from textual.widgets import Static


class FlashLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class FlashMessage:
    text: str
    level: FlashLevel = FlashLevel.INFO
    created_at: float = field(default_factory=monotonic)


# Color map per level (Dracula theme)
_COLORS = {
    FlashLevel.INFO: "cyan",
    FlashLevel.WARN: "yellow",
    FlashLevel.ERROR: "red",
}

_ICONS = {
    FlashLevel.INFO: "i",
    FlashLevel.WARN: "!",
    FlashLevel.ERROR: "x",
}


class FlashBar(Static):
    """A single-line status bar that shows the latest flash message."""

    DEFAULT_CSS = """
    FlashBar {
        height: 1;
        dock: bottom;
        background: #282a36;
        color: #f8f8f2;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__("")
        self._current: FlashMessage | None = None
        self._clear_timer = None

    def flash(self, text: str, level: FlashLevel = FlashLevel.INFO, duration: float = 6.0):
        """Show a flash message that auto-clears after duration seconds."""
        self._current = FlashMessage(text, level)
        color = _COLORS[level]
        icon = _ICONS[level]
        self.update(f"[{color}][{icon}] {text}[/{color}]")

        # Cancel previous timer
        if self._clear_timer is not None:
            self._clear_timer.stop()
        self._clear_timer = self.set_timer(duration, self._clear)

    def flash_error(self, text: str, duration: float = 8.0):
        """Convenience for error-level flash."""
        self.flash(text, FlashLevel.ERROR, duration)

    def flash_warn(self, text: str, duration: float = 6.0):
        """Convenience for warn-level flash."""
        self.flash(text, FlashLevel.WARN, duration)

    def _clear(self):
        self._current = None
        self.update("")
