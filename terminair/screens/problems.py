"""Problems screen."""

from __future__ import annotations

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from terminair.dbt.models import ModelState
from terminair.dbt.regression import RegressionAnalyzer
from terminair.screens.base import DbtScreen
from terminair.widgets.filter_input import FilterInput


class ProblemsScreen(DbtScreen):
    """Active failures and regression signals."""

    CSS = """
    ProblemsScreen {
        layout: vertical;
        background: #1b1d2a;
    }

    #problems-header,
    #problems-meta,
    #failure-heading,
    #signal-heading {
        height: auto;
        padding: 0 1;
        background: #24263a;
        color: #f8f8f2;
    }

    #problems-header {
        padding-top: 1;
    }

    #failure-table,
    #signal-table {
        height: 1fr;
        background: #11131c;
    }
    """

    BINDINGS = DbtScreen.BINDINGS + [
        Binding("enter", "open_selected_detail", "Open"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._signals = []
        self._signal_key_map: dict[str, str] = {}
        self._previous_models: list[ModelState] = []

    async def _load_models(self) -> None:
        provider = self.app_typed.get_data_provider()
        models = await provider.get_models()
        self._models = list(models)
        self._previous_models = await provider.get_previous_models()
        self._sync_selected_model()
        self._refresh_display()

    def compose(self):
        with Vertical():
            yield Static("dbt problems", id="problems-header")
            yield Static("", id="problems-meta")
            yield FilterInput()
            yield Static("active failures", id="failure-heading")
            yield DataTable(id="failure-table")
            yield Static("regression signals", id="signal-heading")
            yield DataTable(id="signal-table")

    def on_mount(self) -> None:
        self._queue_reload()

    def _refresh_display(self) -> None:
        failures = [m for m in self._models if m.status == "failed"]
        failures = self._matching_models(failures)
        self._signals = RegressionAnalyzer(self._models).analyze(previous=self._previous_models or None)
        signals = self._filter_signals(self._signals)

        self._render_failures(failures)
        self._render_signals(signals)
        self._update_meta(len(failures), len(signals))

    def _filter_signals(self, signals):
        query = self._filter_query.lower()
        if not query:
            return list(signals)
        result = []
        for signal in signals:
            candidate = " ".join(
                [
                    signal.node_id,
                    signal.name,
                    signal.signal_type,
                    signal.severity,
                    signal.description,
                    signal.detail,
                ]
            ).lower()
            if query in candidate:
                result.append(signal)
        return result

    def _render_failures(self, failures) -> None:
        table = self.query_one("#failure-table", DataTable)
        table.clear(columns=True)
        table.add_column("model", key="model")
        table.add_column("cause", key="cause")
        table.add_column("status", key="status")
        table.add_column("duration", key="duration")
        table.add_column("rows", key="rows")
        table.add_column("error", key="error")
        for model in failures:
            cause = "upstream" if model.has_upstream_failure else "self"
            table.add_row(
                model.name,
                Text(cause, style="yellow" if cause == "upstream" else "red"),
                Text(model.status, style="bold red"),
                "" if model.duration_s is None else f"{model.duration_s:.1f}s",
                "" if model.rows_written is None else str(model.rows_written),
                (model.error_message or "")[:80],
                key=model.node_id,
            )

    def _render_signals(self, signals) -> None:
        table = self.query_one("#signal-table", DataTable)
        table.clear(columns=True)
        table.add_column("severity", key="severity")
        table.add_column("signal", key="signal")
        table.add_column("model", key="model")
        table.add_column("detail", key="detail")
        self._signal_key_map = {}
        for index, signal in enumerate(signals):
            key = f"signal:{index}:{signal.node_id}"
            self._signal_key_map[key] = signal.node_id
            severity_style = {
                "critical": "bold red",
                "warning": "bold yellow",
                "info": "dim",
            }.get(signal.severity, "white")
            table.add_row(
                Text(signal.severity, style=severity_style),
                signal.signal_type,
                signal.name,
                signal.description,
                key=key,
            )

    def _update_meta(self, failures: int, signals: int) -> None:
        meta = self.query_one("#problems-meta", Static)
        meta.update(
            f"{failures} failures  |  {signals} signals  |  filter: {self._filter_query or 'none'}"
        )

    def action_open_selected_detail(self) -> None:
        if self._selected_model_id:
            self._open_detail(self._selected_model_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        node_id = self._resolve_row_key(event.data_table, str(event.row_key))
        if node_id:
            self._set_selected_model(node_id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        node_id = self._resolve_row_key(event.data_table, str(event.row_key))
        if node_id:
            self._open_detail(node_id)

    def _resolve_row_key(self, table: DataTable, row_key: str) -> str:
        if table.id == "signal-table":
            return self._signal_key_map.get(row_key, "")
        return row_key
