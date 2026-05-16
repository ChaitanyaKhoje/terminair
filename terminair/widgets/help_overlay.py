"""Help screen - modal overlay with keybindings."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """\
[bold cyan] Terminair Keybindings [/bold cyan]

[bold]Navigation[/bold]
   [cyan]<1>[/cyan]        Model list
   [cyan]<2>[/cyan]        Problems
   [cyan]<3>[/cyan]        Lineage
   [cyan]<4>[/cyan]        Detail
   [cyan]<Enter>[/cyan]    Open selected model
   [cyan]<Esc>[/cyan]      Back to parent

[bold]Actions[/bold]
   [cyan]</>[/cyan]        Filter current view
   [cyan]<:>[/cyan]        Command palette
   [cyan]<r>[/cyan]        Refresh
   [cyan]<t>[/cyan]        Cycle model tag filter
   [cyan]<m>[/cyan]        Lineage model mode
   [cyan]<g>[/cyan]        Lineage group mode
   [cyan]<+/-[/cyan]      Lineage depth

[bold]Commands[/bold]
   [cyan]<:models>[/cyan]        Switch to model list
   [cyan]<:problems>[/cyan]      Switch to problems
   [cyan]<:lineage>[/cyan]       Switch to lineage
   [cyan]<:detail>[/cyan]        Switch to detail
   [cyan]<:filter <expr>>[/cyan]  Filter view
   [cyan]<:export json>[/cyan]    Export current view

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
