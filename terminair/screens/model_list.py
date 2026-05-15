"""Model list screen."""

from __future__ import annotations

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.timer import Timer
from textual.widgets import DataTable, Static

from terminair.dbt.models import ModelState
from terminair.dbt.regression import RegressionAnalyzer
from terminair.screens.base import DbtScreen
from terminair.widgets.filter_input import FilterInput


def _status_text(model: ModelState) -> Text:
    style_map = {
        "running": "bold cyan",
        "success": "bold green",
        "failed": "bold red",
        "queued": "bold yellow",
        "skipped": "dim",
    }
    return Text(model.status, style=style_map.get(model.status, "white"))


class ModelListScreen(DbtScreen):
    """All dbt models in a dense table with tag filtering."""

    CSS = """
    ModelListScreen {
        layout: vertical;
        background: #1b1d2a;
    }

    #model-list-header {
        height: auto;
        padding: 1 1 0 1;
        color: #f8f8f2;
        background: #24263a;
    }

    #model-list-meta {
        height: auto;
        padding: 0 1 1 1;
        color: #a5b4fc;
        background: #24263a;
    }

    #model-list-tags {
        height: auto;
        padding: 0 1 1 1;
        color: #f8f8f2;
        background: #24263a;
    }

    #model-table {
        height: 1fr;
        background: #11131c;
    }

    #model-list-status {
        height: auto;
        padding: 0 1 1 1;
        color: #a5b4fc;
        background: #24263a;
    }
    """

    BINDINGS = DbtScreen.BINDINGS + [
        Binding("t", "cycle_tag_filter", "Tag"),
        Binding("enter", "open_selected_detail", "Open"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._selected_tag = "all"
        self._tags: list[str] = []
        self._clock_timer: Timer | None = None

    def compose(self):
        with Vertical():
            yield Static("dbt models", id="model-list-header")
            yield Static("", id="model-list-meta")
            yield Static("", id="model-list-tags")
            yield FilterInput()
            yield DataTable(id="model-table")
            yield Static("", id="model-list-status")

    async def on_mount(self) -> None:
        await self._load_models()

    def on_screen_resume(self) -> None:
        self._clock_timer = self.set_interval(1.0, self._update_header)

    def on_screen_suspend(self) -> None:
        if self._clock_timer is not None:
            self._clock_timer.stop()
            self._clock_timer = None

    def _filtered_models(self) -> list[ModelState]:
        models = self._models
        if self._selected_tag != "all":
            models = [m for m in models if self._selected_tag in m.all_tags or m.tag == self._selected_tag]
        return self._matching_models(models)

    def _render(self) -> None:
        table = self.query_one("#model-table", DataTable)
        table.clear(columns=True)
        table.add_column("status", key="status")
        table.add_column("model", key="model")
        table.add_column("tag", key="tag")
        table.add_column("status_text", key="status_text")
        table.add_column("duration", key="duration")
        table.add_column("rows", key="rows")
        table.add_column("row_delta", key="row_delta")
        table.add_column("dag_id", key="dag_id")

        visible_models = self._filtered_models()
        for model in visible_models:
            table.add_row(
                Text("■", style=_status_text(model).style),
                model.name,
                model.tag,
                _status_text(model),
                "" if model.duration_s is None else f"{model.duration_s:.1f}s",
                "" if model.rows_written is None else str(model.rows_written),
                "" if model.row_delta_pct is None else f"{model.row_delta_pct:+.1f}%",
                model.dag_id,
                key=model.node_id,
            )

        self._tags = sorted({tag for model in self._models for tag in model.all_tags} or {m.tag for m in self._models})
        self._update_meta()
        self._update_tag_bar()
        self._update_statusbar()

        if visible_models:
            selected = next((i for i, model in enumerate(visible_models) if model.node_id == self._selected_model_id), 0)
            table.move_cursor(row=selected)
            self._set_selected_model(visible_models[selected].node_id)

    def _update_meta(self) -> None:
        meta = self.query_one("#model-list-meta", Static)
        total = len(self._models)
        visible = len(self._filtered_models())
        meta.update(f"{visible} visible of {total} models  |  filter: {self._filter_query or 'none'}")

    def _update_tag_bar(self) -> None:
        tags = ["all", *self._tags]
        parts = []
        for tag in tags:
            if tag == self._selected_tag:
                parts.append(f"[reverse]{tag}[/reverse]")
            else:
                parts.append(f"[dim]{tag}[/dim]")
        self.query_one("#model-list-tags", Static).update("tag filter: " + "  ".join(parts))

    def _update_header(self) -> None:
        config = self.app_typed.get_config()
        conn = config.connections.get(config.settings.default_connection)
        url = conn.url if conn else "demo"
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.query_one("#model-list-header", Static).update(
            f"dbt models  |  {url}  |  {ts}"
        )

    def _update_statusbar(self) -> None:
        signals = RegressionAnalyzer(self._models).analyze()
        # NOTE: grain/upstream signals (grain_added, grain_removed,
        # upstream_schema_change) require a previous snapshot via the
        # `previous` argument. Without run_results_previous_path configured,
        # those signals are always absent and this count is conservative.
        warnings = sum(1 for s in signals if s.severity in ("critical", "warning"))
        self.query_one("#model-list-status", Static).update(
            f"{len(self._models)} models  |  {warnings} row-delta regression warnings"
        )

    def action_cycle_tag_filter(self) -> None:
        tags = ["all", *self._tags]
        if not tags:
            return
        current = tags.index(self._selected_tag) if self._selected_tag in tags else 0
        self._selected_tag = tags[(current + 1) % len(tags)]
        self._render()

    def action_open_selected_detail(self) -> None:
        if self._selected_model_id:
            self._open_detail(self._selected_model_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._set_selected_model(str(event.row_key))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_detail(str(event.row_key))
