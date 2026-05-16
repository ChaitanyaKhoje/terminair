"""Model detail screen."""

from __future__ import annotations

import json

from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, TabbedContent, TabPane

from terminair.dbt.models import ModelState
from terminair.dbt.regression import RegressionAnalyzer
from terminair.screens.base import DbtScreen


class ModelDetailScreen(DbtScreen):
    """Tabbed model detail view."""

    CSS = """
    ModelDetailScreen {
        layout: vertical;
        background: #1b1d2a;
    }

    #detail-header {
        height: auto;
        padding: 1 1 0 1;
        background: #24263a;
        color: #f8f8f2;
    }

    #detail-subheader {
        height: auto;
        padding: 0 1 1 1;
        background: #24263a;
        color: #a5b4fc;
    }

    #detail-tabs {
        height: 1fr;
        background: #11131c;
    }

    .detail-pane {
        padding: 1 1;
    }

    #detail-sql-scroll {
        height: 1fr;
    }
    """

    # NOTE: Keys 1-4 intentionally shadow app-level screen-switching bindings while
    # ModelDetailScreen is active. This matches the SCR-04 requirement ("keys 1-5
    # switch to the corresponding tab"). Users return to the model list with Esc/q,
    # not by pressing a number key from the detail view. See 04-01-PLAN.md Task 3.
    BINDINGS = DbtScreen.BINDINGS + [
        Binding("enter", "noop", "Open"),
        Binding("1", "switch_tab('tab-status')", "Status", show=False),
        Binding("2", "switch_tab('tab-structure')", "Structure", show=False),
        Binding("3", "switch_tab('tab-refs')", "Refs", show=False),
        Binding("4", "switch_tab('tab-sql')", "SQL", show=False),
        Binding("5", "switch_tab('tab-regression')", "Regression", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
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
            yield Static("dbt model detail", id="detail-header")
            yield Static("", id="detail-subheader")
            with TabbedContent(id="detail-tabs"):
                yield TabPane("Status", Static("", id="detail-status", classes="detail-pane"), id="tab-status")
                yield TabPane("Structure", Static("", id="detail-structure", classes="detail-pane"), id="tab-structure")
                yield TabPane(
                    "Variables+Refs",
                    Static("", id="detail-refs", classes="detail-pane"),
                    id="tab-refs",
                )
                with TabPane("SQL", id="tab-sql"):
                    with VerticalScroll(id="detail-sql-scroll"):
                        yield Static("", id="detail-sql", classes="detail-pane")
                yield TabPane(
                    "Regression",
                    Static("", id="detail-regression", classes="detail-pane"),
                    id="tab-regression",
                )

    def on_mount(self) -> None:
        self._queue_reload()

    def _refresh_display(self) -> None:
        model = self._current_model()
        if model is None:
            return
        self._update_header(model)
        self.query_one("#detail-status", Static).update(self._render_status(model))
        self.query_one("#detail-structure", Static).update(self._render_structure(model))
        self.query_one("#detail-refs", Static).update(self._render_refs(model))
        self.query_one("#detail-sql", Static).update(self._render_sql(model))
        self.query_one("#detail-regression", Static).update(self._render_regression(model))

    def _current_model(self) -> ModelState | None:
        if self._selected_model_id:
            model = self._find_model(self._selected_model_id)
            if model is not None:
                return model
        return self._models[0] if self._models else None

    def _update_header(self, model: ModelState) -> None:
        self.query_one("#detail-header", Static).update(f"{model.name}  •  {model.status}")
        self.query_one("#detail-subheader", Static).update(
            f"{model.tag}  |  {model.materialization}  |  dag {model.dag_id or '—'}"
        )

    def _render_status(self, model: ModelState) -> str:
        bits = [
            f"status: {model.status}",
            f"duration: {model.duration_s if model.duration_s is not None else '—'}",
            f"rows: {model.rows_written if model.rows_written is not None else '—'}",
            f"row delta: {model.row_delta_pct:+.1f}%" if model.row_delta_pct is not None else "row delta: —",
            f"bytes scanned: {model.bytes_scanned if model.bytes_scanned is not None else '—'}",
            f"upstream failure: {'yes' if model.has_upstream_failure else 'no'}",
            f"error: {model.error_message or '—'}",
        ]
        return "\n".join(bits)

    def _render_structure(self, model: ModelState) -> str:
        bits = [
            f"node: {model.node_id}",
            f"schema: {model.schema_name}",
            f"database: {model.database_name}",
            f"all tags: {', '.join(model.all_tags) or '—'}",
            f"grain: {', '.join(model.grain_columns) or '—'}",
            f"upstream: {', '.join(model.upstream_deps) or '—'}",
            f"downstream: {', '.join(model.downstream_deps) or '—'}",
        ]
        return "\n".join(bits)

    def _render_refs(self, model: ModelState) -> str:
        payload = {
            "refs": model.refs,
            "sources": model.sources,
            "dbt_vars": model.dbt_vars,
            "config": model.config_block,
        }
        return json.dumps(payload, indent=2, default=str)

    def _render_sql(self, model: ModelState) -> str:
        return model.compiled_sql or "-- compiled SQL unavailable --"

    def _render_regression(self, model: ModelState) -> str:
        previous = self._previous_models or None
        all_signals = RegressionAnalyzer(self._models).analyze(previous=previous)
        signals = [s for s in all_signals if s.node_id == model.node_id]
        if not signals:
            return "No regression signals for this model."
        lines = []
        for signal in signals:
            lines.append(f"{signal.severity.upper()}: {signal.signal_type} — {signal.description}")
        return "\n".join(lines)

    def action_noop(self) -> None:
        return None

    def action_switch_tab(self, tab_id: str) -> None:
        try:
            self.query_one("#detail-tabs", TabbedContent).active = tab_id
        except Exception as e:
            self._flash_error(f"Tab {tab_id} not found: {str(e)[:60]}")
