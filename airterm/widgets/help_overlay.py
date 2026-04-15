"""Help screen - modal overlay with keybindings."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold cyan] AirTerm Keybindings [/bold cyan]

[bold]Navigation[/bold]
   [cyan]<1>[/cyan]        DAGs overview
   [cyan]<2>[/cyan]        Recent activity
   [cyan]<3>[/cyan]        Pools
   [cyan]<4>[/cyan]        Health
   [cyan]<5>[/cyan]        Import errors
   [cyan]<Enter>[/cyan]    Drill into selected item
   [cyan]<Esc>[/cyan]      Back to parent

[bold]Actions[/bold]
   [cyan]</>[/cyan]        Filter current view
   [cyan]<:>[/cyan]        Command palette
   [cyan]<r>[/cyan]        Refresh
   [cyan]<g>[/cyan]        DAG graph
   [cyan]<h>[/cyan]        Task history

[bold]Commands[/bold]
   [cyan]<:dag <id>>[/cyan]        Jump to DAG
   [cyan]<:pools>[/cyan]           Switch to pools
   [cyan]<:health>[/cyan]          Switch to health
   [cyan]<:ctx <name>>[/cyan]      Switch connection
   [cyan]<:filter <expr>>[/cyan]   Filter view
   [cyan]<:export json>[/cyan]     Export current view

[bold]General[/bold]
   [cyan]<?>[/cyan]        Toggle this help
   [cyan]<q>[/cyan]        Quit
   [cyan]<Ctrl+C>[/cyan]   Quit

[dim]Press any key to close[/dim]
"""


class HelpScreen(ModalScreen):
    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-content {
        width: 52;
        height: auto;
        background: #44475a;
        border: round #bd93f9;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-content")

    def on_key(self, event) -> None:
        self.dismiss()


# Keep old name for any existing imports
HelpOverlay = HelpScreen
