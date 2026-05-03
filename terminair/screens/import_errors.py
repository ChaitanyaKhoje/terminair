"""Import Errors screen with date distribution graph and hover detail."""

from collections import Counter

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class ImportErrorsScreen(Screen):
    SCROLLABLE = False

    CSS = """
    ImportErrorsScreen {
        layout: vertical;
        background: #282a36;
        overflow: hidden hidden;
    }

    #errors-header {
        height: 3;
        background: #282a36;
        padding: 0 1;
    }

    #errors-graph {
        height: 7;
        background: $panel;
        padding: 0 2;
        margin: 0 1;
    }

    #errors-table {
        height: 1fr;
        border: round #6272a4;
        border-title-color: #bd93f9;
        border-title-align: left;
        margin: 0 1;
        background: #282a36;
    }

    #errors-detail {
        height: 3;
        background: $panel;
        padding: 0 2;
        margin: 0 1;
    }

    #errors-footer {
        height: 1;
        background: #44475a;
        color: #6272a4;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._errors = []

    def compose(self) -> ComposeResult:
        yield Static("", id="errors-header")
        yield Static("[dim]No data[/dim]", id="errors-graph")
        yield DataTable(id="errors-table")
        yield Static("", id="errors-detail")
        yield Static("  <import-errors>", id="errors-footer")

    def on_mount(self) -> None:
        table = self.query_one("#errors-table", DataTable)
        table.add_columns("Filename", "Error", "Detected")
        table.cursor_type = "row"
        table.border_title = "import-errors(0)"
        sep = " [dim]·[/dim] "

        def bind(key: str, desc: str) -> str:
            return f"[cyan]<{key}>[/cyan] [dim]{desc}[/dim]"

        title = " [bold]Import Errors[/bold]  [dim]│[/dim]  [dim]DAG parse failures[/dim]"
        nav = sep.join([bind("esc", "Back"), bind("q", "Quit")])
        self.query_one("#errors-header", Static).update(
            "\n".join([title, "", f" [dim]{'session':9}[/dim] {nav}"])
        )

    def on_data_table_row_highlighted(self, event) -> None:
        if not self._errors or event.cursor_row >= len(self._errors):
            return
        err = self._errors[event.cursor_row]
        ts = str(err.timestamp)[:19] if err.timestamp else "unknown"
        lines = [ln for ln in err.stack_trace.strip().split("\n") if ln.strip()]
        snippet = " | ".join(lines[-2:]) if len(lines) >= 2 else (lines[0] if lines else "")
        self.query_one("#errors-detail").update(
            f"[dim]First seen:[/dim] [yellow]{ts}[/yellow]  "
            f"[dim]File:[/dim] [cyan]{err.filename}[/cyan]\n"
            f"[dim]{snippet[:160]}[/dim]"
        )

    def update_errors(self, errors: list):
        self._errors = errors
        table = self.query_one("#errors-table", DataTable)
        table.clear()

        if not errors:
            table.border_title = "import-errors(0)"
            self.query_one("#errors-graph").update("[green]No import errors[/green]")
            self.query_one("#errors-detail").update("")
            return

        table.border_title = f"[red]import-errors({len(errors)})[/red]"

        for err in errors:
            ts = str(err.timestamp)[:19] if err.timestamp else ""
            lines = [ln for ln in err.stack_trace.strip().split("\n") if ln.strip()]
            snippet = lines[-1][:60] if lines else ""
            table.add_row(err.filename, snippet, ts)

        # Date distribution bar chart
        date_counts: Counter = Counter()
        for err in errors:
            if err.timestamp:
                date_counts[str(err.timestamp)[:10]] += 1
            else:
                date_counts["unknown"] += 1

        max_count = max(date_counts.values()) if date_counts else 1
        bar_width = 24
        chart_lines = [f"[bold]Errors by date[/bold]  ({len(errors)} total)"]
        for date in sorted(date_counts.keys())[-5:]:
            n = date_counts[date]
            fill = int((n / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * fill + "░" * (bar_width - fill)
            chart_lines.append(f"  {date}  [red]{bar}[/red]  {n}")
        self.query_one("#errors-graph").update("\n".join(chart_lines))
