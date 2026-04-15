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
        sep = " [dim]·[/dim] "

        def bind(key: str, desc: str) -> str:
            return f"[cyan]<{key}>[/cyan] [dim]{desc}[/dim]"

        title = (
            " [bold red]Currently Broken[/bold red]  [dim]│[/dim]  "
            "[dim]import · failed runs · SLA breaches[/dim]"
        )
        # Separate session actions (Back/Quit) from screen navigation so
        # we don't mix session keys into the screens row. Also omit the
        # redundant `Errors` entry since this is the Errors screen itself.
        screens_nav = sep.join(
            [
                bind("2", "Pools"),
                bind("3", "Health"),
                bind("4", "SLA"),
                bind("5", "Time"),
                bind("0", "Watchlist"),
            ]
        )
        session_nav = sep.join([bind("esc", "Back"), bind("q", "Quit")])

        def section(label: str, keys: str) -> str:
            return f" [dim]{label:9}[/dim] {keys}"

        self.query_one("#broken-header", Static).update(
            "\n".join([title, "", section("screens", screens_nav), section("session", session_nav)])
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
