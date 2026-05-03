"""DAGs overview screen - k9s style layout."""

import asyncio as _asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static

from terminair.widgets.filter_input import FilterInput


class DagsScreen(Screen):
    SCROLLABLE = False

    CSS = """
    DagsScreen {
        layout: vertical;
        background: #282a36;
        overflow: hidden hidden;
    }

    #dags-header {
        height: 6;
        background: #282a36;
        padding: 0 1;
    }

    #dags-table {
        height: 1fr;
        border: round #6272a4;
        border-title-color: #bd93f9;
        border-title-align: left;
        margin: 0 1;
        background: #282a36;
    }

    #dags-footer {
        height: 1;
        background: #44475a;
        color: #6272a4;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("enter", "drill_in", "Drill In", priority=True),
        Binding("/", "show_filter", "Filter", priority=True),
        Binding("b", "bookmark", "Bookmark"),
        Binding("w", "toggle_wrap", "Wrap"),
    ]

    def __init__(self):
        super().__init__()
        self.id = "dags-screen"
        self._all_dags = []
        self._filter_text = ""
        self._wrap_mode = False
        self._filter_live_task = None

    def compose(self) -> ComposeResult:
        yield Static("", id="dags-header")
        yield DataTable(id="dags-table")
        yield FilterInput(id="dags-filter-bar")
        yield Static("  <dags>", id="dags-footer")

    def on_mount(self) -> None:
        table = self.query_one("#dags-table", DataTable)
        table.add_columns(
            "DAG ID",
            "Owner",
            "Schedule",
            "State",
            "Last Run",
            "Duration",
            "Next Run",
            "Active",
        )
        table.cursor_type = "row"
        table.border_title = "dags(0)[0]"
        self._refresh_header()
        self._load_from_app()

    # ── header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):
        try:
            app = self.app
            conn, user = "n/a", "n/a"
            if hasattr(app, "_config") and app._config:
                cfg = app._config
                dc = cfg.settings.default_connection
                conn_obj = cfg.connections.get(dc)
                if conn_obj:
                    conn = conn_obj.url.replace("http://", "").replace("https://", "")
                    if hasattr(conn_obj.auth, "username"):
                        user = conn_obj.auth.username or "n/a"

            def bind(key: str, desc: str) -> str:
                return f"[cyan]<{key}>[/cyan] [dim]{desc}[/dim]"

            sep = " [dim]·[/dim] "
            meta = (
                "[bold]DAGs[/bold]  [dim]│[/dim]  "
                f"[dim]conn[/dim] [cyan]{conn}[/cyan]  [dim]│[/dim]  "
                f"[dim]user[/dim] [yellow]{user}[/yellow]  [dim]│[/dim]  "
                "[green]v0.1.0[/green]"
            )
            row_screens = sep.join(
                [
                    bind("1", "Errors"),
                    bind("2", "Pools"),
                    bind("3", "Health"),
                    bind("4", "SLA"),
                    bind("5", "Time"),
                    bind("0", "Watchlist"),
                ]
            )
            row_session = sep.join(
                [
                    bind("enter", "Drill"),
                    bind("esc", "Back"),
                    bind("/", "Filter"),
                    bind("w", "Wrap"),
                    bind("r", "Refresh"),
                    bind("b", "Bookmark"),
                ]
            )
            row_dag = sep.join(
                [
                    bind("h", "History"),
                    bind("d", "Deps"),
                    bind(":", "Cmd"),
                    bind("q", "Quit"),
                ]
            )

            def section(label: str, keys: str) -> str:
                return f" [dim]{label:9}[/dim] {keys}"

            text = "\n".join(
                [
                    " " + meta,
                    "",
                    section("screens", row_screens),
                    section("session", row_session),
                    section("dag", row_dag),
                ]
            )
            self.query_one("#dags-header", Static).update(text)
        except Exception:
            pass

    # ── wrap toggle ───────────────────────────────────────────────────────────

    def action_toggle_wrap(self) -> None:
        self._wrap_mode = not self._wrap_mode
        table = self.query_one("#dags-table", DataTable)
        saved_title = table.border_title
        table.clear(columns=True)
        if self._wrap_mode:
            table.add_columns("DAG ID", "Schedule", "State", "Last Run")
        else:
            table.add_columns(
                "DAG ID",
                "Owner",
                "Schedule",
                "State",
                "Last Run",
                "Duration",
                "Next Run",
                "Active",
            )
        table.cursor_type = "row"
        table.border_title = saved_title
        self._render_table()

    # ── filter ────────────────────────────────────────────────────────────────

    def action_show_filter(self) -> None:
        fb = self.query_one("#dags-filter-bar", FilterInput)
        fb.open(on_change=self._on_filter_change, on_close=self._on_filter_close)

    def _on_filter_change(self, text: str) -> None:
        self._filter_text = text.lower()
        self._render_table()

        # Start/stop a background fetcher that refreshes the DAG list
        # every 5s while the user is actively filtering.
        try:
            if text and (self._filter_live_task is None or self._filter_live_task.done()):
                self._filter_live_task = _asyncio.create_task(self._filter_live_loop())
            elif not text and self._filter_live_task:
                self._filter_live_task.cancel()
                self._filter_live_task = None
        except Exception:
            pass

    def _on_filter_close(self) -> None:
        # Cancel any live filter worker when the filter bar is closed.
        try:
            if self._filter_live_task and not self._filter_live_task.done():
                self._filter_live_task.cancel()
        except Exception:
            pass
        self._filter_live_task = None

    async def _filter_live_loop(self) -> None:
        try:
            while True:
                fb = self.query_one("#dags-filter-bar", FilterInput)
                if not fb.display:
                    break
                val = fb.current_value
                if not val:
                    break
                # Trigger the app to refresh the DAG list from the server.
                try:
                    await self.app._load_dags()
                except Exception:
                    pass
                await _asyncio.sleep(5)
        except Exception:
            pass
        finally:
            self._filter_live_task = None

    # ── navigation ────────────────────────────────────────────────────────────

    def key_enter(self) -> None:
        self.app.action_drill_in()

    def action_drill_in(self) -> None:
        self.app.action_drill_in()

    # ── bookmark ──────────────────────────────────────────────────────────────

    def action_bookmark(self) -> None:
        table = self.query_one("#dags-table", DataTable)
        if table.cursor_row is None:
            return
        dags = self._all_dags
        if not dags or table.cursor_row >= len(dags):
            return

        # Filter may have changed which DAGs are displayed
        visible_dags = dags
        if self._filter_text:
            visible_dags = [d for d in dags if self._filter_text in d.dag_id.lower()]
        if table.cursor_row >= len(visible_dags):
            return

        dag_id = visible_dags[table.cursor_row].dag_id
        watchlist = getattr(self.app, "_watchlist", [])
        if dag_id in watchlist:
            watchlist.remove(dag_id)
        else:
            watchlist.append(dag_id)
        self.app._watchlist = watchlist
        self._render_table()

    # ── data ──────────────────────────────────────────────────────────────────

    def _load_from_app(self):
        try:
            state = getattr(self.app, "_cached_dags", None)
            if state:
                self.update_dags(state)
        except Exception:
            pass

    def update_dags(self, dags: list):
        self._all_dags = dags
        self._render_table()

    def _render_table(self):
        table = self.query_one("#dags-table", DataTable)
        table.clear()

        dags = self._all_dags
        if self._filter_text:
            dags = [d for d in dags if self._filter_text in d.dag_id.lower()]

        watchlist = getattr(self.app, "_watchlist", [])
        count, total = len(dags), len(self._all_dags)

        # Border title: show filter inline when active
        if self._filter_text:
            table.border_title = (
                f"dags({count}/{total})[0] "
                f"[dim][[/dim][yellow]/{self._filter_text}[/yellow][dim]][/dim]"
            )
        else:
            table.border_title = f"dags({count})[0]"

        # Footer: show filter hint when active
        footer = self.query_one("#dags-footer", Static)
        if self._filter_text:
            footer.update(
                f"  <dags>  [dim]filter:[/dim] [yellow]/{self._filter_text}[/yellow]  [dim]<esc> clear[/dim]"
            )
        else:
            footer.update("  <dags>")

        for dag in dags:
            is_paused = dag.is_paused
            prefix = "★ " if dag.dag_id in watchlist else ""
            state = "[dim]paused[/dim]" if is_paused else "[green]active[/green]"
            if self._wrap_mode:
                table.add_row(
                    prefix + dag.dag_id,
                    dag.schedule_interval or dag.timetable_description or "",
                    state,
                    dag.next_dagrun or "",
                )
            else:
                table.add_row(
                    prefix + dag.dag_id,
                    ", ".join(dag.owners) if dag.owners else "",
                    dag.schedule_interval or dag.timetable_description or "",
                    state,
                    dag.next_dagrun or "",
                    "",
                    "",
                    "[dim]no[/dim]" if is_paused else "[green]yes[/green]",
                )
