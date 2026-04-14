"""Filter bar widget - inline bottom bar for filtering tables."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input, Label
from textual.containers import Horizontal


class FilterInput(Widget):
    """Inline filter bar. Esc clears+closes; Enter keeps filter and closes."""

    CSS = """
    FilterInput {
        height: 1;
        background: #44475a;
        layout: horizontal;
    }
    FilterInput Label {
        color: #bd93f9;
        width: auto;
        padding: 0 0 0 1;
        height: 1;
    }
    FilterInput Input {
        background: #44475a;
        border: none;
        height: 1;
        padding: 0;
        color: #f8f8f2;
        width: 1fr;
    }
    FilterInput Input:focus {
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel_filter", "Cancel", priority=True),
    ]

    def __init__(self, on_change=None, on_close=None, **kwargs):
        super().__init__(**kwargs)
        self._on_change = on_change
        self._on_close = on_close
        self.display = False

    def compose(self) -> ComposeResult:
        yield Label("/")
        yield Input(placeholder="filter...", id="filter-field")

    def open(self, on_change=None, on_close=None):
        if on_change:
            self._on_change = on_change
        if on_close:
            self._on_close = on_close
        self.display = True
        inp = self.query_one("#filter-field", Input)
        inp.value = ""
        inp.focus()

    def close(self, clear: bool = False):
        self.display = False
        if clear:
            inp = self.query_one("#filter-field", Input)
            inp.value = ""
            if self._on_change:
                self._on_change("")
        try:
            self.app.screen.query_one("DataTable").focus()
        except Exception:
            pass

    @property
    def current_value(self) -> str:
        try:
            return self.query_one("#filter-field", Input).value
        except Exception:
            return ""

    def action_cancel_filter(self):
        """Esc: clear filter and close."""
        self.close(clear=True)

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._on_change:
            self._on_change(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter: keep filter active, close the bar."""
        self.close(clear=False)
