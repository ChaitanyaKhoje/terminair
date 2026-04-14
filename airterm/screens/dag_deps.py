"""DAG Dependency Impact screen - shows what breaks if this DAG fails."""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


class DagDepsScreen(Screen):
    """Shows upstream producers and downstream consumers for a DAG via datasets."""

    CSS = """
    DagDepsScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 6;
    }

    #deps-table {
        height: 100%;
    }

    #deps-summary {
        height: 100%;
        background: $panel;
        padding: 0 2;
        overflow-y: auto;
    }
    """

    def __init__(self):
        super().__init__()
        self._dag_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield DataTable(id="deps-table")
        yield Static("", id="deps-summary")

    def on_mount(self) -> None:
        table = self.query_one("#deps-table")
        table.add_columns(
            "DAG ID",
            "Relationship",
            "Dataset URI",
            "Last Event",
        )

    def set_context(self, dag_id: str):
        self._dag_id = dag_id

    def update_deps(self, deps: list, dag_id: str):
        table = self.query_one("#deps-table")
        table.clear()

        if not deps:
            self.query_one("#deps-summary").update(
                f"[bold]{dag_id}[/bold]\n"
                f"──────────────────────────────────────\n"
                f"No dataset dependencies found.\n"
                f"This DAG does not produce or consume any datasets."
            )
            return

        producers = [d for d in deps if d["relationship"] == "produces"]
        consumers = [d for d in deps if d["relationship"] == "consumes"]

        for dep in deps:
            table.add_row(
                dep["dag_id"],
                dep["relationship"],
                dep["dataset_uri"],
                dep.get("last_event", ""),
            )

        self.query_one("#deps-summary").update(
            f"[bold]Impact Analysis: {dag_id}[/bold]\n"
            f"──────────────────────────────────────\n"
            f"Produces {len(producers)} dataset(s) | "
            f"{len(consumers)} downstream DAG(s) consume them\n"
            f"If [bold]{dag_id}[/bold] fails, {len(consumers)} DAG(s) may be affected."
        )
