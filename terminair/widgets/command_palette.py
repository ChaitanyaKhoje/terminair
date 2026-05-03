"""Command palette widget."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input


class CommandPalette(Widget):
    CSS = """
    CommandPalette {
        dock: top;
        height: 3;
        background: $panel;
        border-bottom: solid $accent;
    }

    CommandPalette Input {
        background: $surface;
        color: $text;
    }

    .hint {
        color: $text-muted;
    }
    """

    def __init__(self):
        super().__init__()
        self.display = False

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder=":dag <name> :pools :health :ctx <name> :filter :export", id="cmd-input"
        )

    def show(self):
        self.display = True
        self.query_one("#cmd-input").focus()

    def hide(self):
        self.display = False

    def on_input_submitted(self, event: Input.Submitted):
        self.hide()
        if event.value:
            self.app.action_execute_command(event.value)


class CommandExecutor:
    """Parses and executes command palette commands."""

    COMMANDS = {
        "dag": "jump_to_dag",
        "pools": "switch_pools",
        "health": "switch_health",
        "errors": "switch_errors",
        "recent": "switch_recent",
        "ctx": "switch_connection",
        "filter": "apply_filter",
        "export": "export_data",
        "set": "set_option",
        "theme": "switch_theme",
    }

    # Commands that require exactly one argument
    _REQUIRES_ARG = {"dag", "ctx", "theme"}
    # Commands that take no arguments
    _NO_ARGS = {"pools", "health", "errors", "recent"}
    # Commands that take optional/variable args
    _OPTIONAL_ARGS = {"filter", "export", "set"}

    @classmethod
    def parse(cls, cmd: str) -> tuple:
        parts = cmd.strip().split()
        if not parts:
            return None, []
        return parts[0], parts[1:]

    @classmethod
    def validate(cls, cmd_name: str, args: list) -> bool:
        """Validate command name and argument count."""
        if cmd_name not in cls.COMMANDS:
            return False
        if cmd_name in cls._REQUIRES_ARG and len(args) != 1:
            return False
        if cmd_name in cls._NO_ARGS and len(args) != 0:
            return False
        return True

    @classmethod
    def execute(cls, app, cmd: str):
        cmd_name, args = cls.parse(cmd)
        if not cls.validate(cmd_name, args):
            try:
                from terminair.widgets.flash import FlashBar
                app.query_one(FlashBar).flash_warn(f"Invalid command: {cmd}")
            except Exception:
                pass
            return False

        action = cls.COMMANDS[cmd_name]
        if hasattr(app, f"action_{action}"):
            getattr(app, f"action_{action}")(*args)
            return True
        return False
