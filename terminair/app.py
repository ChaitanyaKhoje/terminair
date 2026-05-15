# ruff: noqa: UP017
"""Textual App subclass for Terminair."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from terminair.config import Config
from terminair.dbt.aggregator import StateAggregator
from terminair.dbt.artifacts import ArtifactReader
from terminair.dbt.manifest import ManifestLoader
from terminair.dbt.mock_data import MockDataProvider
from terminair.dbt.snowflake_client import SnowflakeClient
from terminair.logging_utils import get_logger
from terminair.screens import (
    LineageScreen,
    ModelDetailScreen,
    ModelListScreen,
    ProblemsScreen,
)
from terminair.themes.dark import DARK_CSS
from terminair.widgets.command_palette import CommandExecutor, CommandPalette
from terminair.widgets.flash import FlashBar

if TYPE_CHECKING:
    from textual.timer import Timer

_logger = get_logger("terminair.app")


class TerminairApp(App):
    CSS = DARK_CSS
    ENABLE_COMMAND_PALETTE = False
    SCREENS = {
        "model_list": ModelListScreen,
        "problems": ProblemsScreen,
        "lineage": LineageScreen,
        "detail": ModelDetailScreen,
    }
    DEFAULT_AUTO_FOCUS = ""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding(":", "command_palette", "Command"),
        Binding("1", "switch_model_list", "Models"),
        Binding("2", "switch_problems", "Problems"),
        Binding("3", "switch_lineage", "Lineage"),
        Binding("4", "switch_detail", "Detail"),
    ]

    def __init__(self, config: Config, demo_mode: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._config = config
        self._demo_mode = demo_mode
        self._nav_stack: list[tuple] = []
        self._auto_refresh_enabled = False
        self._last_refresh_at: datetime | None = None
        self._live_timer: Timer | None = None
        self._data_provider = None
        self.selected_model_id: str = ""

    def compose(self) -> ComposeResult:
        yield CommandPalette()
        yield Static("", id="refresh-status")
        yield FlashBar()

    def _flash_error(self, text: str):
        """Show an error message in the flash bar."""
        try:
            self.query_one(FlashBar).flash_error(text)
        except Exception:
            pass

    def _flash_warn(self, text: str):
        """Show a warning message in the flash bar."""
        try:
            self.query_one(FlashBar).flash_warn(text)
        except Exception:
            pass

    def _touch_refresh(self) -> None:
        self._last_refresh_at = datetime.now(timezone.utc)
        self._update_refresh_status()

    def _build_data_provider(self):
        if self._demo_mode:
            _logger.info("Starting Terminair in demo mode")
            return MockDataProvider()

        active_connection = self._config.connections.get(
            self._config.settings.default_connection
        )
        if active_connection is None or active_connection.dbt is None:
            _logger.warning("No dbt configuration found — using demo data")
            self._flash_warn("No dbt configuration — running demo data")
            return MockDataProvider()

        dbt_config = active_connection.dbt
        manifest_path = dbt_config.manifest_path
        if manifest_path is None or not manifest_path.exists():
            _logger.warning(
                "dbt manifest missing at %s — using demo data",
                manifest_path or "<unset>",
            )
            path_label = manifest_path.name if manifest_path else "<unset>"
            self._flash_warn(f"dbt manifest missing ({path_label}) — using demo data")
            return MockDataProvider()

        try:
            manifest = ManifestLoader(manifest_path)
            results_path = dbt_config.run_results_path or manifest_path.with_name(
                "run_results.json"
            )
            artifacts = ArtifactReader(
                results_path,
                dbt_config.run_results_previous_path,
            )
        except Exception as exc:
            _logger.warning("dbt data layer unavailable — using demo data: %s", exc)
            self._flash_warn("dbt data layer unavailable — using demo data")
            return MockDataProvider()

        bridge = None
        if active_connection.url and active_connection.auth is not None:
            try:
                from terminair.dbt.airflow_bridge import AirflowBridge

                bridge = AirflowBridge(active_connection)
            except Exception as exc:
                _logger.warning("Airflow bridge unavailable — continuing without it: %s", exc)
                self._flash_warn("Airflow bridge unavailable — continuing without it")

        snowflake = None
        if active_connection.snowflake is not None:
            try:
                snowflake = SnowflakeClient()
            except Exception as exc:
                _logger.warning("Snowflake client unavailable — continuing without it: %s", exc)

        return StateAggregator(
            manifest,
            artifacts,
            bridge=bridge,
            snowflake=snowflake,
        )

    def get_data_provider(self):
        if self._data_provider is None:
            self._data_provider = self._build_data_provider()
        return self._data_provider

    def _update_refresh_status(self) -> None:
        try:
            bar = self.query_one("#refresh-status", Static)
        except Exception:
            return
        interval = self._config.settings.refresh_interval
        live = self._auto_refresh_enabled
        ts = self._last_refresh_at
        ts_s = ts.strftime("%Y-%m-%d %H:%M:%S UTC") if ts else "—"
        live_part = f"[yellow]LIVE[/yellow] every {interval}s  " if live else ""
        bar.update(f" {live_part}[dim]last refresh[/dim] [cyan]{ts_s}[/cyan]")

    def _schedule_live_reload(self) -> None:
        pass

    def action_toggle_live(self) -> None:
        if self._auto_refresh_enabled:
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self) -> None:
        if self._live_timer is not None:
            return
        sec = float(self._config.settings.refresh_interval)
        self._live_timer = self.set_interval(sec, self._schedule_live_reload, name="terminair_live")
        self._auto_refresh_enabled = True
        self._update_refresh_status()

    def _stop_watch(self) -> None:
        if self._live_timer is not None:
            self._live_timer.stop()
            self._live_timer = None
        self._auto_refresh_enabled = False
        self._update_refresh_status()

    # ── Manual refresh (r key) ───────────────────────────────────────────────

    def action_refresh(self):
        pass

    # ── Screen switching ─────────────────────────────────────────────────────

    def _switch_to(self, screen_name: str) -> bool:
        """Pop to floor screen, then push the target screen.

        Returns True if a switch was performed, False if already on that
        screen (no-op).
        """
        target_cls = self.SCREENS.get(screen_name)
        try:
            if target_cls and isinstance(self.screen, target_cls):
                return False
        except Exception:
            pass

        if self._auto_refresh_enabled:
            self._stop_watch()
        while len(self.screen_stack) > 2:
            self.pop_screen()
        self.push_screen(screen_name)
        return True

    # ── Navigation ───────────────────────────────────────────────────────────

    def action_focus_filter(self):
        try:
            from terminair.widgets.filter_input import FilterInput

            filter_bar = self.screen.query_one(FilterInput)
            filter_bar.open()
        except Exception:
            pass

    def action_command_palette(self):
        try:
            palette = self.query_one("#command-palette")
            palette.show()
        except Exception:
            pass

    def action_back(self):
        if len(self.screen_stack) > 2:
            self.pop_screen()

    def action_execute_command(self, cmd: str):
        if not cmd:
            return
        CommandExecutor.execute(self, cmd)

    def action_export_data(self, *args):
        pass

    def action_jump_to_dag(self, dag_id: str = ""):
        pass

    def action_switch_model_list(self):
        self._switch_to("model_list")

    def action_switch_problems(self):
        self._switch_to("problems")

    def action_switch_lineage(self):
        self._switch_to("lineage")

    def action_switch_detail(self, model_id: str = ""):
        if model_id:
            self.selected_model_id = model_id
        if not self.selected_model_id:
            return
        self._switch_to("detail")

    def action_switch_theme(self, theme: str = "dark"):
        pass

    def action_switch_connection(self, ctx: str = ""):
        pass

    def action_apply_filter(self, filter_str: str = ""):
        try:
            screen = self.screen
            if hasattr(screen, "_on_filter_change"):
                screen._on_filter_change(filter_str)  # type: ignore[attr-defined]
        except Exception:
            pass

    def action_set_option(self, key: str = "", value: str = ""):
        pass

    def action_quit(self):
        self.exit()

    def get_config(self) -> Config:
        return self._config

    def on_mount(self) -> None:
        self.get_data_provider()
        self._switch_to("model_list")
