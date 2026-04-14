"""Textual App subclass for AirTerm."""

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from airterm.api.client import AirflowClient
from airterm.api.poller import Poller
from airterm.config import Config
from airterm.screens.dag_detail import DagDetailScreen
from airterm.screens.dag_graph import DAGGraphScreen
from airterm.screens.dag_runs import DagRunsScreen
from airterm.screens.dags import DagsScreen
from airterm.screens.event_log import EventLogScreen
from airterm.screens.health import HealthScreen
from airterm.screens.import_errors import ImportErrorsScreen
from airterm.screens.pools import PoolsScreen
from airterm.screens.recent_activity import RecentActivityScreen
from airterm.screens.sla_misses import SlaMissScreen
from airterm.screens.task_history import TaskHistoryScreen
from airterm.screens.task_instances import TaskInstancesScreen
from airterm.screens.xcom_viewer import XComViewerScreen
from airterm.themes.dark import DARK_CSS
from airterm.widgets.command_palette import CommandPalette, CommandExecutor


class AirTermApp(App):
    CSS = DARK_CSS
    ENABLE_COMMAND_PALETTE = False
    SCREENS = {
        "dags": DagsScreen,
        "dag_detail": DagDetailScreen,
        "task_instances": TaskInstancesScreen,
        "dag_graph": DAGGraphScreen,
        "recent_activity": RecentActivityScreen,
        "pools": PoolsScreen,
        "health": HealthScreen,
        "import_errors": ImportErrorsScreen,
        "event_log": EventLogScreen,
        "task_history": TaskHistoryScreen,
        "xcom_viewer": XComViewerScreen,
        "sla_misses": SlaMissScreen,
    }
    DEFAULT_AUTO_FOCUS = ""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding(":", "command_palette", "Command"),
        Binding("1", "switch_dags", "DAGs"),
        Binding("2", "switch_recent", "Recent"),
        Binding("3", "switch_pools", "Pools"),
        Binding("4", "switch_health", "Health"),
        Binding("5", "switch_errors", "Errors"),
        Binding("h", "view_task_history", "Task History"),
        Binding("g", "view_graph", "Graph"),
        Binding("6", "switch_sla", "SLA"),
        Binding("x", "view_xcoms", "XComs"),
    ]

    def __init__(self, config: Config, **kwargs):
        super().__init__(**kwargs)
        self._config = config
        self._client: Optional[AirflowClient] = None
        self._poller: Optional[Poller] = None
        self._nav_stack: list[tuple] = []

    def compose(self) -> ComposeResult:
        yield CommandPalette()

    def on_mount(self) -> None:
        from textual.app import asyncio

        asyncio.create_task(self._init_app())

    async def _init_app(self) -> None:
        conn = self._config.connections.get(self._config.settings.default_connection)
        if not conn:
            self._show_error("No connection configured. Run with --url or configure in config.")
            return

        self._check_environment_badging(conn.url)

        self._client = AirflowClient(conn)
        self._poller = Poller(self._client)

        try:
            dags_result = await self._client.get_dags(limit=100)
        except Exception as e:
            err_msg = str(e)
            if "Connection refused" in err_msg or "connect" in err_msg.lower():
                self._show_error(
                    f"Cannot connect to {conn.url}\n\nIs Airflow running? Check the URL."
                )
            elif "401" in err_msg or "403" in err_msg or "Unauthorized" in err_msg:
                self._show_error(f"Authentication failed.\n\nCheck username and password.")
            else:
                self._show_error(f"Connection error: {err_msg[:100]}")
            return

        if not dags_result or not dags_result.dags:
            self._show_error(
                "Connected but no DAGs found.\n\nIf this is wrong, check Airflow is running."
            )
            return

        self._cached_dags = dags_result.dags
        self.push_screen("dags")
        await self._load_initial_data()

    async def _load_initial_data(self):
        poller = self._poller
        if not poller:
            return
        await poller.start_polling(
            "dags",
            self._config.settings.refresh_interval,
            limit=100,
        )

    def action_switch_dags(self):
        while len(self.screen_stack) > 2:
            self.pop_screen()

    def action_switch_recent(self):
        self.push_screen("recent_activity")
        self._load_recent_activity()

    def action_switch_pools(self):
        self.push_screen("pools")
        self._load_pools()

    def action_switch_health(self):
        self.push_screen("health")
        self._load_health()

    def action_switch_errors(self):
        self.push_screen("import_errors")
        self._load_import_errors()

    def action_switch_sla(self):
        self.push_screen("sla_misses")
        from textual.app import asyncio
        asyncio.create_task(self._load_sla_misses())

    def action_view_xcoms(self):
        """Open XCom viewer for the selected task in the current task instances screen."""
        try:
            table = self.screen.query_one("#task-instances-table")
        except Exception:
            return
        if table is None or table.cursor_row is None:
            return
        # Get context from the task instances screen
        dag_id, run_id = self.screen.get_context()
        if not dag_id or not run_id:
            return
        try:
            row = table.get_row_at(table.cursor_row)
            task_id = row[0]
        except Exception:
            return
        self.push_screen("xcom_viewer")
        from textual.app import asyncio
        asyncio.create_task(self._load_xcoms(dag_id, run_id, task_id))

    async def _load_sla_misses(self):
        from datetime import datetime, timezone
        try:
            client = self._client
            if not client:
                return
            # Get all currently running DAG runs
            running_result = await client.get_all_dag_runs(limit=100)
            running = [r for r in running_result.dag_runs if r.state and r.state.value == "running"]

            if not running:
                self.screen.update_sla([], 0)
                return

            # Collect historical durations per dag_id to compute P95
            dag_durations: dict[str, list[float]] = {}
            for run in running_result.dag_runs:
                if run.start_date and run.end_date:
                    dag_durations.setdefault(run.dag_id, []).append(
                        (run.end_date - run.start_date).total_seconds()
                    )

            now = datetime.now(timezone.utc)
            breaches = []
            for run in running:
                if not run.start_date:
                    continue
                running_for = (now - run.start_date).total_seconds()
                durations = dag_durations.get(run.dag_id, [])
                if len(durations) < 3:
                    continue
                sorted_d = sorted(durations)
                p95 = sorted_d[int(len(sorted_d) * 0.95)]
                if running_for > p95:
                    breaches.append({
                        "dag_id": run.dag_id,
                        "run_id": run.dag_run_id,
                        "state": run.state.value,
                        "running_for": running_for,
                        "p95": p95,
                        "over_by": running_for - p95,
                        "started": str(run.start_date)[:19],
                    })

            self.screen.update_sla(breaches, len(running))
        except Exception:
            pass

    async def _load_xcoms(self, dag_id: str, run_id: str, task_id: str):
        try:
            client = self._client
            if not client:
                return
            screen = self.screen
            screen.set_context(dag_id, run_id, task_id)
            result = await client.get_xcom_entries(dag_id, run_id, task_id)
            screen.update_xcoms(result.xcom_entries)
        except Exception:
            pass

    async def _load_recent_activity(self):
        try:
            client = self._client
            if not client:
                return
            runs_result = await client.get_all_dag_runs(limit=50)
            screen = self.screen.query_one("#activity-table")
            empty = self.screen.query_one("#activity-empty")
            if not runs_result.dag_runs:
                empty.display = True
                screen.display = False
                return
            screen.display = True
            empty.display = False
            table = self.screen.query_one("#activity-table")
            table.clear()
            for run in runs_result.dag_runs:
                duration = ""
                if run.start_date and run.end_date:
                    delta = run.end_date - run.start_date
                    duration = f"{int(delta.total_seconds())}s"
                table.add_row(
                    str(run.end_date)[:19] if run.end_date else "",
                    run.dag_id,
                    run.dag_run_id[:30],
                    run.state.value if run.state else "",
                    duration,
                    "",
                )
        except Exception:
            pass

    async def _load_pools(self):
        try:
            client = self._client
            if not client:
                return
            pools_result = await client.get_pools()
            self.screen.update_pools(pools_result.pools)
        except Exception:
            pass

    async def _load_health(self):
        try:
            client = self._client
            if not client:
                return
            health_result = await client.get_health()
            screen = self.screen.query_one("#health-content")
            if hasattr(screen, "update"):
                screen.update(health_result)
        except Exception:
            pass

    async def _load_import_errors(self):
        try:
            client = self._client
            if not client:
                return
            errors_result = await client.get_import_errors()
            table = self.screen.query_one("#import-errors-table")
            table.clear()
            for error in errors_result.import_errors:
                table.add_row(
                    error.filename,
                    error.stack_trace[:50] if error.stack_trace else "",
                    str(error.timestamp)[:19] if error.timestamp else "",
                )
        except Exception:
            pass

    async def _load_event_logs(self):
        try:
            client = self._client
            if not client:
                return
            logs_result = await client.get_event_logs(limit=50)
            table = self.screen.query_one("#event-log-table")
            table.clear()
            for log in logs_result.event_logs:
                table.add_row(
                    str(log.when)[:19] if log.when else "",
                    log.dag_id or "",
                    log.event if log.event else "",
                    log.owner if log.owner else "",
                )
        except Exception:
            pass

    def action_view_task_history(self):
        dags = getattr(self, "_cached_dags", [])
        try:
            table = self.screen.query_one("#dags-table")
        except Exception:
            table = None
        if not dags or table is None or table.cursor_row is None:
            return
        dag = dags[table.cursor_row]
        self.push_screen("task_history")
        from textual.app import asyncio
        asyncio.create_task(self._load_task_history(dag.dag_id))

    def action_view_graph(self):
        dags = getattr(self, "_cached_dags", [])
        try:
            table = self.screen.query_one("#dags-table")
        except Exception:
            table = None
        if not dags or table is None or table.cursor_row is None:
            return
        dag = dags[table.cursor_row]
        self.push_screen("dag_graph")
        from textual.app import asyncio
        asyncio.create_task(self._load_dag_graph(dag.dag_id))

    async def _load_dag_graph(self, dag_id: str):
        try:
            client = self._client
            if not client:
                return
            task_list = await client.get_dag_tasks(dag_id)
            tasks = [{"id": t.task_id} for t in task_list.tasks]
            edges = []
            for task in task_list.tasks:
                for downstream in task.downstream_task_ids:
                    edges.append((task.task_id, downstream))
            self.screen.render_graph(tasks, edges)
        except Exception:
            pass

    async def _load_task_history(self, dag_id: str):
        try:
            client = self._client
            if not client:
                return
            runs_result = await client.get_dag_runs(dag_id, limit=20)
            all_entries = []
            failure_count = 0
            total_duration = 0.0
            total_retries = 0
            count = 0
            for run in runs_result.dag_runs:
                state = run.state.value if run.state else ""
                duration = 0.0
                if run.start_date and run.end_date:
                    duration = (run.end_date - run.start_date).total_seconds()
                    total_duration += duration
                if state == "failed":
                    failure_count += 1
                all_entries.append({
                    "run_id": run.dag_run_id,
                    "state": state,
                    "duration": duration,
                    "try_number": "",
                })
                count += 1
            failure_rate = (failure_count / count * 100) if count else 0.0
            avg_duration = (total_duration / count) if count else 0.0
            recent_states = [e["state"] for e in all_entries[:10]]
            pattern = " ".join(["✓" if s == "success" else "✗" for s in recent_states])
            screen = self.screen
            screen.set_context("(all tasks)", dag_id)
            screen.update_history(all_entries, failure_rate, avg_duration, total_retries, pattern)
        except Exception:
            pass

    def action_view_dag_detail(self, dag_id: str = ""):
        self._nav_stack.append(("dags", dag_id))
        self.push_screen("dag_detail")

    def action_drill_in(self):
        try:
            table = self.screen.query_one("#dags-table")
        except Exception:
            return
        if table and table.cursor_row is not None:
            dags = getattr(self, "_cached_dags", [])
            if dags and table.cursor_row < len(dags):
                dag = dags[table.cursor_row]
                self._nav_stack.append(("dags", dag.dag_id))
                self.push_screen("dag_detail")
                from textual.app import asyncio

                asyncio.create_task(self._load_dag_detail(dag.dag_id))

    async def _load_dag_detail(self, dag_id: str):
        from airterm.metrics.aggregations import (
            compute_duration_stats,
            compute_streak,
            compute_success_rate,
            find_last_failure,
        )
        from airterm.metrics.sparkline import compute_sparkline
        try:
            client = self._client
            if not client:
                return
            runs_result = await client.get_dag_runs(dag_id, limit=50)
            dag_info = await client.get_dag(dag_id)
            runs = runs_result.dag_runs

            durations = [
                (r.end_date - r.start_date).total_seconds()
                for r in runs if r.start_date and r.end_date
            ]
            stats = compute_duration_stats(runs)
            avg_duration = stats.get("avg", 0.0)

            screen = self.screen
            screen.update_runs(runs, avg_duration)

            streak = compute_streak(runs)
            success_rate = compute_success_rate(runs) * 100
            success_count = sum(1 for r in runs if r.state and r.state.value == "success")
            failure_count = sum(1 for r in runs if r.state and r.state.value == "failed")
            last_failure = find_last_failure(runs)
            last_failure_str = str(last_failure.execution_date)[:16] if last_failure else ""
            sparkline = compute_sparkline(durations)
            schedule = dag_info.schedule_interval or dag_info.timetable_description or "n/a"
            owner = ", ".join(dag_info.owners) if dag_info.owners else "n/a"

            screen.update_metrics(
                dag_id=dag_id,
                schedule=schedule,
                owner=owner,
                total_runs=len(runs),
                success_count=success_count,
                failure_count=failure_count,
                success_rate=success_rate,
                avg_duration=avg_duration,
                p95_duration=stats.get("p95", 0.0),
                streak_type=streak.get("type", ""),
                streak_count=streak.get("count", 0),
                sparkline=sparkline,
                last_failure=last_failure_str,
                runs=runs,
            )
        except Exception:
            pass

    def action_focus_filter(self):
        try:
            from airterm.widgets.filter_input import FilterInput

            filter_bar = self.screen.query_one(FilterInput)
            filter_bar.open()
        except Exception:
            pass

    def action_refresh(self):
        try:
            current = self.screen_stack[-1] if self.screen_stack else None
            if hasattr(current, "refresh"):
                current.refresh()
        except Exception:
            pass

    def action_command_palette(self):
        try:
            palette = self.query_one("#command-palette")
            palette.show()
        except Exception:
            pass

    def action_back(self):
        # stack[0] = base compose screen, stack[1] = DagsScreen (root nav level)
        # Don't pop below DagsScreen
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

    def _show_error(self, message: str):
        from textual.widgets import Static

        error_screen = Static(
            f"""
╭──────────────────────────────────────────────╮
│         Cannot Connect to Airflow             │
╰──────────────────────────────────────────────╯

{message}

Press q to quit and try:
• Check Airflow is running
• Verify the URL is correct
• Check credentials
""",
            markup=True,
        )
        error_screen.styles.height = "100%"
        error_screen.styles.width = "100%"
        self.mount(error_screen)

    def _check_environment_badging(self, url: str) -> None:
        if "prod" in url.lower():
            self.styles.border = ("double", "#ff5555")
            try:
                header = self.query_one("#header-bar")
                title = header.update_title("PROD")
            except Exception:
                pass

    def get_client(self) -> Optional[AirflowClient]:
        return self._client

    def get_poller(self) -> Optional[Poller]:
        return self._poller

    def get_config(self) -> Config:
        return self._config
