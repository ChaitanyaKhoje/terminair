"""Currently Broken — combined summary of import errors, failed runs, and SLA misses."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class BrokenSummaryScreen(Screen):
    SCROLLABLE = False

    CSS = """
    BrokenSummaryScreen {
        layout: vertical;
        background: #282a36;
        overflow: hidden hidden;
    }

    #broken-header {
        height: 4;
        background: #282a36;
        padding: 0 1;
    }

    #broken-table {
        height: 1fr;
        border: round #ff5555;
        border-title-color: #ff5555;
        border-title-align: left;
        margin: 0 1;
        background: #282a36;
    }

    #broken-footer {
        height: 1;
        background: #44475a;
        color: #6272a4;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="broken-header")
        yield DataTable(id="broken-table")
        yield Static("  <broken>", id="broken-footer")

    def on_mount(self) -> None:
        table = self.query_one("#broken-table", DataTable)
        table.add_columns("Category", "Item", "Detail", "Since")
        table.cursor_type = "row"
        table.border_title = "broken(0)"
        self._refresh_header()

    def _refresh_header(self):
        self.query_one("#broken-header", Static).update(
            " [bold red]Currently Broken[/bold red]  "
            "[dim]import errors · failed runs · SLA breaches[/dim]\n"
            " \n"
            " [dim]<[/dim][cyan]esc[/cyan][dim]>[/dim] Back  "
            "[dim]<[/dim][cyan]3[/cyan][dim]>[/dim] Pools  "
            "[dim]<[/dim][cyan]4[/cyan][dim]>[/dim] Health  "
            "[dim]<[/dim][cyan]5[/cyan][dim]>[/dim] Errors  "
            "[dim]<[/dim][cyan]6[/cyan][dim]>[/dim] SLA  "
            "[dim]<[/dim][cyan]7[/cyan][dim]>[/dim] Timeline  "
            "[dim]<[/dim][cyan]q[/cyan][dim]>[/dim] Quit"
        )

    def update_broken(self, items: list):
        table = self.query_one("#broken-table", DataTable)
        table.clear()
        if not items:
            table.border_title = "[green]broken(0) — all clear[/green]"
            return
        table.border_title = f"[red]broken({len(items)})[/red]"
        for item in items:
            cat = item.get("category", "")
            cat_color = {
                "import_error": "red",
                "failed_run": "red",
                "sla_breach": "yellow",
            }.get(cat, "white")
            table.add_row(
                f"[{cat_color}]{item.get('category_label', cat)}[/{cat_color}]",
                item.get("item", ""),
                item.get("detail", ""),
                item.get("since", ""),
            )
