"""Footer bar widget with key hints."""

from textual.widgets import Static


class FooterBar(Static):
    def __init__(self):
        super().__init__("")
        self.id = "footer-bar"

    def update_keys(self, keys: list[tuple[str, str]]):
        parts = []
        for key, desc in keys:
            parts.append(f"[cyan]<{key}>[/cyan] [white]{desc}[/white]")
        self.update("  ".join(parts))
