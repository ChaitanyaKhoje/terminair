"""Settings drawer widget - toggleable side panel."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Static


class SettingsDrawer(Widget):
    """Toggleable settings drawer panel."""

    CSS = """
    SettingsDrawer {
        dock: right;
        width: 30;
        background: #44475a;
        display: none;
    }
    SettingsDrawer.visible {
        display: block;
    }
    SettingsDrawer .setting-section {
        padding: 1 2;
        height: auto;
    }
    SettingsDrawer .setting-label {
        color: #bd93f9;
    }
    SettingsDrawer .setting-value {
        color: #f8f8f2;
    }
    """

    BINDINGS = [
        Binding("s", "toggle", "Toggle", priority=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.display = False

    def compose(self) -> ComposeResult:
        yield Static("Settings", classes="setting-section setting-label")
        yield Static("Theme: Dark", classes="setting-section")
        yield Static("Auto-refresh: On", classes="setting-section")
        yield Static("Refresh: 30s", classes="setting-section")

    def show(self):
        self.display = True
        self.add_class("visible")

    def hide(self):
        self.display = False
        self.remove_class("visible")

    def toggle(self):
        if self.display:
            self.hide()
        else:
            self.show()

    def action_toggle(self):
        self.toggle()
