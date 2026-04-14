"""DAGs overview screen - k9s style layout."""

import re
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Static

from airterm.widgets.filter_input import FilterInput


class DagsScreen(Screen):
    SCROLLABLE = False

    CSS = """
    DagsScreen {
        layout: vertical;
        background: #282a36;
        overflow: hidden hidden;
    }

    #dags-header {
        height: 4;
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

    def compose(self) -> ComposeResult:
        yield Static("", id="dags-header")
        yield DataTable(id="dags-table")
        yield FilterInput(id="dags-filter-bar")
        yield Static("  <dags>", id="dags-footer")

    def on_mount(self) -> None:
        table = self.query_one("#dags-table", DataTable)
        table.add_columns(
            "DAG ID", "Owner", "Schedule", "State",
            "Last Run", "Duration", "Next Run", "Active",
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

            left_lines = [
                f" [dim]Connection:[/dim] [cyan]{conn}[/cyan]",
                f" [dim]User:[/dim]       [yellow]{user}[/yellow]",
                f" [dim]AirTerm:[/dim]    [green]v0.1.0[/green]",
            ]
            hint_lines = [
                " [dim]<[/dim][cyan]2[/cyan][dim]>[/dim] Broken "
                "[dim]<[/dim][cyan]3[/cyan][dim]>[/dim] Pools  "
                "[dim]<[/dim][cyan]4[/cyan][dim]>[/dim] Health "
                "[dim]<[/dim][cyan]5[/cyan][dim]>[/dim] Errors "
                "[dim]<[/dim][cyan]6[/cyan][dim]>[/dim] SLA "
                "[dim]<[/dim][cyan]7[/cyan][dim]>[/dim] Timeline "
                "[dim]<[/dim][cyan]0[/cyan][dim]>[/dim] Watchlist",

                " [dim]<[/dim][cyan]enter[/cyan][dim]>[/dim] Drill  "
                "[dim]<[/dim][cyan]esc[/cyan][dim]>[/dim] Back  "
                "[dim]<[/dim][cyan]/[/cyan][dim]>[/dim] Filter  "
                "[dim]<[/dim][cyan]w[/cyan][dim]>[/dim] Wrap  "
                "[dim]<[/dim][cyan]b[/cyan][dim]>[/dim] Bookmark",

                " [dim]<[/dim][cyan]g[/cyan][dim]>[/dim] Graph  "
                "[dim]<[/dim][cyan]h[/cyan][dim]>[/dim] History  "
                "[dim]<[/dim][cyan]d[/cyan][dim]>[/dim] Deps  "
                "[dim]<[/dim][cyan]:[/cyan][dim]>[/dim] Cmd  "
                "[dim]<[/dim][cyan]q[/cyan][dim]>[/dim] Quit",
            ]
            pad = 38
            lines = []
            for l, h in zip(left_lines, hint_lines):
                plain = re.sub(r"\[.*?\]", "", l)
                lines.append(l + " " * max(0, pad - len(plain)) + h)
            self.query_one("#dags-header", Static).update("\n".join(lines))
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
                "DAG ID", "Owner", "Schedule", "State",
                "Last Run", "Duration", "Next Run", "Active",
            )
        table.cursor_type = "row"
        table.border_title = saved_title
        self._render_table()

    # ── filter ────────────────────────────────────────────────────────────────

    def action_show_filter(self) -> None:
        fb = self.query_one("#dags-filter-bar", FilterInput)
        fb.open(on_change=self._on_filter_change)

    def _on_filter_change(self, text: str) -> None:
        self._filter_text = text.lower()
        self._render_table()

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

    def update_footer_live(self, is_live: bool):
        footer = self.query_one("#dags-footer", Static)
        base = "  <dags>"
        if self._filter_text:
            base = f"  <dags>  [dim]filter:[/dim] [yellow]/{self._filter_text}[/yellow]  [dim]<esc> clear[/dim]"
        if is_live:
            footer.update(base + "  [bold green][LIVE][/bold green]")
        else:
            footer.update(base)

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
            footer.update(f"  <dags>  [dim]filter:[/dim] [yellow]/{self._filter_text}[/yellow]  [dim]<esc> clear[/dim]")
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
