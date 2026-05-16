"""Shared helpers for dbt screens."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.screen import Screen

from terminair.dbt.models import ModelState
from terminair.widgets.filter_input import FilterInput

if TYPE_CHECKING:
    from terminair.app import TerminairApp


class DbtScreen(Screen):
    """Shared behavior for dbt screens."""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("/", "focus_filter", "Filter"),
        Binding(":", "command_palette", "Command"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._models: list[ModelState] = []
        self._previous_models: list[ModelState] = []
        self._filter_query = ""
        self._selected_model_id = ""

    @property
    def app_typed(self) -> TerminairApp:
        return self.app  # type: ignore[return-value]

    def _provider_models(self) -> Iterable[ModelState]:
        return self._models

    async def _load_models(self) -> None:
        provider = self.app_typed.get_data_provider()
        models = await provider.get_models()
        self._models = list(models)
        self._previous_models = await provider.get_previous_models()
        self._sync_selected_model()
        self._render()

    def _queue_reload(self) -> None:
        self.run_worker(self._load_models(), exclusive=True)

    def action_refresh(self) -> None:
        self._queue_reload()

    def action_focus_filter(self) -> None:
        try:
            filter_bar = self.query_one(FilterInput)
            filter_bar.open(on_change=self._on_filter_change)
        except Exception:
            pass

    def action_command_palette(self) -> None:
        self.app_typed.action_command_palette()

    def action_back(self) -> None:
        self.app_typed.action_back()

    def action_quit(self) -> None:
        self.app_typed.action_quit()

    def _on_filter_change(self, value: str) -> None:
        self._filter_query = value.strip()
        self._render()

    def _set_selected_model(self, node_id: str) -> None:
        self._selected_model_id = node_id
        self.app_typed.selected_model_id = node_id

    def _sync_selected_model(self) -> None:
        if self._selected_model_id:
            for model in self._models:
                if model.node_id == self._selected_model_id:
                    return
        if self._models:
            self._set_selected_model(self._models[0].node_id)

    def _matching_models(self, haystack: Iterable[ModelState]) -> list[ModelState]:
        query = self._filter_query.lower()
        if not query:
            return list(haystack)
        matches: list[ModelState] = []
        for model in haystack:
            candidate = " ".join(
                [
                    model.node_id,
                    model.name,
                    model.tag,
                    model.status,
                    model.dag_id,
                    model.materialization,
                    " ".join(model.all_tags),
                    model.error_message or "",
                ]
            ).lower()
            if query in candidate:
                matches.append(model)
        return matches

    def _open_detail(self, node_id: str) -> None:
        if node_id:
            self._set_selected_model(node_id)
            self.app_typed.action_switch_detail(node_id)

    def _find_model(self, node_id: str) -> ModelState | None:
        return next((model for model in self._models if model.node_id == node_id), None)

    def _render(self) -> None:
        raise NotImplementedError
