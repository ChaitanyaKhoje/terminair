"""Textual App subclass for Terminair."""

import asyncio as _asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.timer import Timer

from terminair.config import Config
from terminair.logging_utils import get_logger, sanitize_error
from terminair.themes.dark import DARK_CSS
from terminair.widgets.command_palette import CommandExecutor, CommandPalette
from terminair.widgets.flash import FlashBar

_logger = get_logger("terminair.app")


class TerminairApp(App):
    CSS = DARK_CSS
    ENABLE_COMMAND_PALETTE = False
    SCREENS = {}
    DEFAULT_AUTO_FOCUS = ""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding(":", "command_palette", "Command"),
    ]

    def __init__(self, config: Config, **kwargs):
        super().__init__(**kwargs)
        self._config = config
        self._nav_stack: list[tuple] = []
        self._auto_refresh_enabled = False
        self._last_refresh_at: datetime | None = None
        self._live_timer: "Timer | None" = None

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
        self._last_refresh_at = datetime.now(UTC)
        self._update_refresh_status()

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

    def action_switch_theme(self, theme: str = "dark"):
        pass

    def action_switch_connection(self, ctx: str = ""):
        pass

    def action_apply_filter(self, filter_str: str = ""):
        pass

    def action_set_option(self, key: str = "", value: str = ""):
        pass

    def action_quit(self):
        self.exit()

    def get_config(self) -> Config:
        return self._config
