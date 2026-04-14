"""Import Errors screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class ImportErrorsScreen(Screen):
    CSS = """
    ImportErrorsScreen {
        layout: grid;
        grid-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="import-errors-table")
        e = Static("No import errors", id="errors-empty")
        e.display = False
        yield e

    def on_mount(self) -> None:
        table = self.query_one("#import-errors-table")
        table.add_columns("Filename", "Timestamp", "Error")

    def update_errors(self, errors: list):
        table = self.query_one("#import-errors-table")
        table.clear()
        empty = self.query_one("#errors-empty")
        if not errors:
            empty.show()
            return
        empty.hide()
        for err in errors:
            table.add_row(
                err.filename,
                str(err.timestamp) if err.timestamp else "",
                err.stack_trace[:100] + "..." if len(err.stack_trace) > 100 else err.stack_trace,
            )
