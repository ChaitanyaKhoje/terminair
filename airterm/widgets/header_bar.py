"""Header bar widget."""

from textual.widgets import Static


class HeaderBar(Static):
    def __init__(self):
        super().__init__("")
        self.id = "header-bar"

    def update_header(
        self,
        title: str = "AirTerm",
        connection: str = "n/a",
        user: str = "n/a",
        version: str = "n/a",
    ):
        left = f" [cyan]{title}[/cyan]  "
        right = f" Context: [cyan]{connection}[/cyan]  User: [yellow]{user}[/yellow]  v{version} "
        self.update(left + right)
        self.styles.content_align = ("left", "top")

    def update_title(self, title: str):
        left = f" [cyan]{title}[/cyan]  "
        self.update(left)
