"""Lineage screen."""

from __future__ import annotations

from collections import defaultdict

from rich.text import Text
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from terminair.dbt.models import ModelState
from terminair.screens.base import DbtScreen
from terminair.widgets.filter_input import FilterInput


class LineageScreen(DbtScreen):
    """ASCII lineage view in model or tag/group mode."""

    CSS = """
    LineageScreen {
        layout: vertical;
        background: #1b1d2a;
    }

    #lineage-header,
    #lineage-meta {
        height: auto;
        padding: 0 1;
        background: #24263a;
        color: #f8f8f2;
    }

    #lineage-header {
        padding-top: 1;
    }

    #lineage-table {
        height: 1fr;
        background: #11131c;
    }
    """

    BINDINGS = DbtScreen.BINDINGS + [
        Binding("m", "model_mode", "Model"),
        Binding("g", "group_mode", "Group"),
        Binding("+", "deeper", "Deeper"),
        Binding("-", "shallower", "Shallower"),
        Binding("enter", "open_selected_detail", "Open"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._mode = "model"
        self._depth = 4
        self._model_map: dict[str, ModelState] = {}

    def compose(self):
        with Vertical():
            yield Static("dbt lineage", id="lineage-header")
            yield Static("", id="lineage-meta")
            yield FilterInput()
            yield DataTable(id="lineage-table")

    async def on_mount(self) -> None:
        await self._load_models()

    def _render(self) -> None:
        self._model_map = {model.node_id: model for model in self._models}
        rows = self._render_model_tree() if self._mode == "model" else self._render_group_list()

        table = self.query_one("#lineage-table", DataTable)
        table.clear(columns=True)
        table.add_column("lineage", key="lineage")
        table.add_column("model", key="model")
        table.add_column("status", key="status")
        table.add_column("tag", key="tag")
        table.add_column("depth", key="depth")

        for node_id, line, depth, model in rows:
            table.add_row(
                Text(line, style="white"),
                model.name,
                Text(model.status, style="bold green" if model.status == "success" else "bold red" if model.status == "failed" else "yellow"),
                model.tag,
                str(depth),
                key=node_id,
            )

        self._update_meta(len(rows))
        if rows:
            visible_ids = [node_id for node_id, _, _, _ in rows]
            selected = next((i for i, node_id in enumerate(visible_ids) if node_id == self._selected_model_id), 0)
            table.move_cursor(row=selected)
            self._set_selected_model(visible_ids[selected])

    def _render_model_tree(self):
        root = self._selected_model_id or (self._models[0].node_id if self._models else "")
        if not root:
            return []
        rows = []

        def visit(node_id: str, prefix: str, depth: int, visited: set[str]) -> None:
            if node_id in visited:
                return
            model = self._model_map.get(node_id)
            if model is None:
                return
            rows.append((node_id, f"{prefix}{model.name}", depth, model))
            if depth >= self._depth:
                return
            visited = set(visited)
            visited.add(node_id)
            children = [dep for dep in model.upstream_deps if dep in self._model_map]
            for index, child_id in enumerate(children):
                branch = "└─ " if index == len(children) - 1 else "├─ "
                visit(child_id, prefix + branch, depth + 1, visited)

        visit(root, "", 0, set())
        return self._filter_rows(rows)

    def _render_group_list(self):
        rows = []
        grouped = defaultdict(list)
        for model in self._models:
            grouped[model.tag].append(model)
        for tag in sorted(grouped):
            for model in sorted(grouped[tag], key=lambda item: item.name):
                line = f"{tag} / {model.name}"
                rows.append((model.node_id, line, 0, model))
        return self._filter_rows(rows)

    def _filter_rows(self, rows):
        if not self._filter_query:
            return rows
        query = self._filter_query.lower()
        filtered = []
        for node_id, line, depth, model in rows:
            candidate = " ".join(
                [
                    node_id,
                    line,
                    model.name,
                    model.tag,
                    model.status,
                    model.dag_id,
                    " ".join(model.all_tags),
                ]
            ).lower()
            if query in candidate:
                filtered.append((node_id, line, depth, model))
        return filtered

    def _update_meta(self, count: int) -> None:
        self.query_one("#lineage-meta", Static).update(
            f"mode: {self._mode}  |  depth: {self._depth}  |  showing {count} rows"
        )

    def action_model_mode(self) -> None:
        self._mode = "model"
        self._render()

    def action_group_mode(self) -> None:
        self._mode = "group"
        self._render()

    def action_deeper(self) -> None:
        self._depth += 1
        self._render()

    def action_shallower(self) -> None:
        self._depth = max(1, self._depth - 1)
        self._render()

    def action_open_selected_detail(self) -> None:
        if self._selected_model_id:
            self._open_detail(self._selected_model_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._set_selected_model(str(event.row_key))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_detail(str(event.row_key))
