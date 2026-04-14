"""Textual App subclass for AirTerm."""

import asyncio as _asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from airterm.api.client import AirflowClient
from airterm.api.poller import Poller
from airterm.config import Config
from airterm.screens.dag_deps import DagDepsScreen
from airterm.screens.dag_detail import DagDetailScreen
from airterm.screens.dag_graph import DAGGraphScreen
from airterm.screens.dags import DagsScreen
from airterm.screens.event_log import EventLogScreen
from airterm.screens.health import HealthScreen
from airterm.screens.import_errors import ImportErrorsScreen
from airterm.screens.pools import PoolsScreen
from airterm.screens.recent_activity import RecentActivityScreen
from airterm.screens.resource_timeline import ResourceTimelineScreen
from airterm.screens.sla_misses import SlaMissScreen
from airterm.screens.task_history import TaskHistoryScreen
from airterm.screens.task_instances import TaskInstancesScreen
from airterm.screens.watchlist import WatchlistScreen
from airterm.screens.xcom_viewer import XComViewerScreen
from airterm.themes.dark import DARK_CSS
from airterm.widgets.command_palette import CommandPalette, CommandExecutor
from airterm.widgets.flash import FlashBar


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
        "dag_deps": DagDepsScreen,
        "resource_timeline": ResourceTimelineScreen,
        "watchlist": WatchlistScreen,
    }
    DEFAULT_AUTO_FOCUS = ""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("w", "toggle_watch", "Watch"),
        Binding(":", "command_palette", "Command"),
        Binding("1", "switch_dags", "DAGs"),
        Binding("2", "switch_recent", "Recent"),
        Binding("3", "switch_pools", "Pools"),
        Binding("4", "switch_health", "Health"),
        Binding("5", "switch_errors", "Errors"),
        Binding("6", "switch_sla", "SLA"),
        Binding("7", "switch_timeline", "Timeline"),
        Binding("0", "switch_watchlist", "Watchlist"),
        Binding("h", "view_task_history", "Task History"),
        Binding("g", "view_graph", "Graph"),
        Binding("d", "view_deps", "Deps"),
        Binding("x", "view_xcoms", "XComs"),
    ]

    def __init__(self, config: Config, **kwargs):
        super().__init__(**kwargs)
        self._config = config
        self._client: Optional[AirflowClient] = None
        self._poller: Optional[Poller] = None
        self._nav_stack: list[tuple] = []
        self._watchlist: list[str] = list(config.settings.watchlist)
        self._auto_refresh_task: Optional[_asyncio.Task] = None
        self._auto_refresh_enabled = False
        # Tracks the context for the active screen so auto-refresh can reload
        self._active_screen_context: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield CommandPalette()
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

    def on_mount(self) -> None:
        _asyncio.create_task(self._init_app())

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

    # ── Auto-refresh (watch mode) ────────────────────────────────────────────

    def action_toggle_watch(self):
        if self._auto_refresh_enabled:
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self):
        self._auto_refresh_enabled = True
        self._auto_refresh_task = _asyncio.create_task(self._watch_loop())
        self._update_live_indicator(True)

    def _stop_watch(self):
        self._auto_refresh_enabled = False
        if self._auto_refresh_task:
            self._auto_refresh_task.cancel()
            self._auto_refresh_task = None
        self._update_live_indicator(False)

    def _update_live_indicator(self, is_live: bool):
        try:
            screen = self.screen
            if hasattr(screen, "update_footer_live"):
                screen.update_footer_live(is_live)
        except Exception:
            pass

    async def _watch_loop(self):
        interval = self._config.settings.refresh_interval
        while self._auto_refresh_enabled:
            await _asyncio.sleep(interval)
            if not self._auto_refresh_enabled:
                break
            try:
                await self._refresh_current_screen()
            except Exception as e:
                self._flash_error(f"Refresh failed: {str(e)[:80]}")

    async def _refresh_current_screen(self):
        """Re-load data for whatever screen is currently active."""
        screen = self.screen
        screen_id = screen.__class__.__name__

        if screen_id == "DagsScreen":
            await self._load_dags()
        elif screen_id == "PoolsScreen":
            await self._load_pools()
        elif screen_id == "HealthScreen":
            await self._load_health()
        elif screen_id == "ImportErrorsScreen":
            await self._load_import_errors()
        elif screen_id == "RecentActivityScreen":
            await self._load_recent_activity()
        elif screen_id == "SlaMissScreen":
            await self._load_sla_misses()
        elif screen_id == "DagDetailScreen" and self._active_screen_context:
            await self._load_dag_detail(self._active_screen_context)
        elif screen_id == "ResourceTimelineScreen":
            await self._load_resource_timeline()
        elif screen_id == "WatchlistScreen":
            await self._load_watchlist()

    async def _load_dags(self):
        try:
            client = self._client
            if not client:
                return
            result = await client.get_dags(limit=100)
            self._cached_dags = result.dags
            self.screen.update_dags(result.dags)
        except Exception as e:
            self._flash_error(f"DAGs load failed: {str(e)[:80]}")

    # ── Screen switching ─────────────────────────────────────────────────────

    def _cancel_watch_on_switch(self):
        """Stop auto-refresh when navigating away."""
        if self._auto_refresh_enabled:
            self._stop_watch()

    def _switch_to(self, screen_name: str):
        """Pop to DagsScreen floor, then push the target screen."""
        self._cancel_watch_on_switch()
        while len(self.screen_stack) > 2:
            self.pop_screen()
        self.push_screen(screen_name)

    def action_switch_dags(self):
        self._cancel_watch_on_switch()
        while len(self.screen_stack) > 2:
            self.pop_screen()

    def action_switch_recent(self):
        self._switch_to("recent_activity")
        _asyncio.create_task(self._load_recent_activity())

    def action_switch_pools(self):
        self._switch_to("pools")
        _asyncio.create_task(self._load_pools())

    def action_switch_health(self):
        self._switch_to("health")
        _asyncio.create_task(self._load_health())

    def action_switch_errors(self):
        self._switch_to("import_errors")
        _asyncio.create_task(self._load_import_errors())

    def action_switch_sla(self):
        self._switch_to("sla_misses")
        _asyncio.create_task(self._load_sla_misses())

    def action_switch_timeline(self):
        self._switch_to("resource_timeline")
        _asyncio.create_task(self._load_resource_timeline())

    def action_switch_watchlist(self):
        self._switch_to("watchlist")
        _asyncio.create_task(self._load_watchlist())

    # ── DAG-context actions (g, h, d — require dags-table selection) ─────────

    def _get_selected_dag_id(self) -> Optional[str]:
        """Get the selected DAG ID from the dags table, or None."""
        dags = getattr(self, "_cached_dags", [])
        try:
            table = self.screen.query_one("#dags-table")
        except Exception:
            return None
        if not dags or table is None or table.cursor_row is None:
            return None
        # Account for filter
        filter_text = getattr(self.screen, "_filter_text", "")
        visible = dags
        if filter_text:
            visible = [d for d in dags if filter_text in d.dag_id.lower()]
        if table.cursor_row >= len(visible):
            return None
        return visible[table.cursor_row].dag_id

    def action_view_task_history(self):
        dag_id = self._get_selected_dag_id()
        if not dag_id:
            return
        self._cancel_watch_on_switch()
        self.push_screen("task_history")
        _asyncio.create_task(self._load_task_history(dag_id))

    def action_view_graph(self):
        dag_id = self._get_selected_dag_id()
        if not dag_id:
            return
        self._cancel_watch_on_switch()
        self.push_screen("dag_graph")
        _asyncio.create_task(self._load_dag_graph(dag_id))

    def action_view_deps(self):
        dag_id = self._get_selected_dag_id()
        if not dag_id:
            return
        self._cancel_watch_on_switch()
        self.push_screen("dag_deps")
        _asyncio.create_task(self._load_dag_deps(dag_id))

    def action_view_xcoms(self):
        """Open XCom viewer for the selected task in the current task instances screen."""
        try:
            table = self.screen.query_one("#task-instances-table")
        except Exception:
            return
        if table is None or table.cursor_row is None:
            return
        dag_id, run_id = self.screen.get_context()
        if not dag_id or not run_id:
            return
        try:
            row = table.get_row_at(table.cursor_row)
            task_id = row[0]
        except Exception:
            return
        self._cancel_watch_on_switch()
        self.push_screen("xcom_viewer")
        _asyncio.create_task(self._load_xcoms(dag_id, run_id, task_id))

    def action_view_dag_detail(self, dag_id: str = ""):
        self._nav_stack.append(("dags", dag_id))
        self.push_screen("dag_detail")

    def action_drill_in(self):
        dag_id = self._get_selected_dag_id()
        if not dag_id:
            return
        self._cancel_watch_on_switch()
        self._nav_stack.append(("dags", dag_id))
        self._active_screen_context = dag_id
        self.push_screen("dag_detail")
        _asyncio.create_task(self._load_dag_detail(dag_id))

    # ── Data loaders ─────────────────────────────────────────────────────────

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
        except Exception as e:
            self._flash_error(f"Recent activity load failed: {str(e)[:80]}")

    async def _load_pools(self):
        try:
            client = self._client
            if not client:
                return
            pools_result = await client.get_pools()
            self.screen.update_pools(pools_result.pools)
        except Exception as e:
            self._flash_error(f"Pools load failed: {str(e)[:80]}")

    async def _load_health(self):
        try:
            client = self._client
            if not client:
                return
            health_result = await client.get_health()
            self.screen.update_health(health_result)
        except Exception as e:
            self._flash_error(f"Health load failed: {str(e)[:80]}")

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
        except Exception as e:
            self._flash_error(f"Import errors load failed: {str(e)[:80]}")

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
                    str(log.event_timestamp)[:19] if log.event_timestamp else "",
                    log.dag_id or "",
                    log.event_type if log.event_type else "",
                    log.owner if log.owner else "",
                )
        except Exception as e:
            self._flash_error(f"Event logs load failed: {str(e)[:80]}")

    async def _load_sla_misses(self):
        from datetime import datetime, timezone
        try:
            client = self._client
            if not client:
                return
            running_result = await client.get_all_dag_runs(limit=100)
            running = [r for r in running_result.dag_runs if r.state and r.state.value == "running"]

            if not running:
                self.screen.update_sla([], 0)
                return

            dag_durations: dict = {}
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
        except Exception as e:
            self._flash_error(f"SLA check failed: {str(e)[:80]}")

    async def _load_xcoms(self, dag_id: str, run_id: str, task_id: str):
        try:
            client = self._client
            if not client:
                return
            screen = self.screen
            screen.set_context(dag_id, run_id, task_id)
            result = await client.get_xcom_entries(dag_id, run_id, task_id)
            screen.update_xcoms(result.xcom_entries)
        except Exception as e:
            self._flash_error(f"XCom load failed: {str(e)[:80]}")

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
        except Exception as e:
            self._flash_error(f"Graph load failed: {str(e)[:80]}")

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
        except Exception as e:
            self._flash_error(f"Task history load failed: {str(e)[:80]}")

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
        except Exception as e:
            self._flash_error(f"DAG detail load failed: {str(e)[:80]}")

    async def _load_dag_deps(self, dag_id: str):
        """Load dataset dependency information for a DAG."""
        try:
            client = self._client
            if not client:
                return

            screen = self.screen
            screen.set_context(dag_id)

            datasets_result = await client.get_datasets()
            events_result = await client.get_dataset_events()

            deps = []

            # Find datasets this DAG produces (it's the source)
            produced_uris = set()
            for event in events_result.dataset_events:
                if event.source_dag_id == dag_id:
                    produced_uris.add(event.dataset_uri)
                    deps.append({
                        "dag_id": dag_id,
                        "relationship": "produces",
                        "dataset_uri": event.dataset_uri,
                        "last_event": str(event.created_at)[:19],
                    })

            # Deduplicate produced datasets
            seen_produced = set()
            unique_produced = []
            for d in deps:
                key = d["dataset_uri"]
                if key not in seen_produced:
                    seen_produced.add(key)
                    unique_produced.append(d)
            deps = unique_produced

            # Find DAGs that consume those datasets (they appear as dataset events
            # from other DAGs, or are in the dataset list and consumed by other DAGs)
            # Since Airflow REST API doesn't directly expose consumer DAGs,
            # we look at all events to find other DAGs that reference these datasets
            consumer_events = {}
            for event in events_result.dataset_events:
                if event.dataset_uri in produced_uris and event.source_dag_id != dag_id:
                    if event.source_dag_id not in consumer_events:
                        consumer_events[event.source_dag_id] = {
                            "dataset_uri": event.dataset_uri,
                            "last_event": str(event.created_at)[:19],
                        }

            for consumer_dag, info in consumer_events.items():
                deps.append({
                    "dag_id": consumer_dag,
                    "relationship": "consumes",
                    "dataset_uri": info["dataset_uri"],
                    "last_event": info["last_event"],
                })

            screen.update_deps(deps, dag_id)
        except Exception as e:
            self._flash_error(f"Dependencies load failed: {str(e)[:80]}")

    async def _load_task_log(self, dag_id: str, run_id: str, task_id: str, try_number: int):
        """Fetch task log and display last 30 lines in task instances screen."""
        try:
            client = self._client
            if not client:
                return
            log_text = await client.get_task_log(dag_id, run_id, task_id, try_number)
            lines = log_text.strip().split("\n")
            tail = "\n".join(lines[-30:])
            self.screen.update_log(task_id, tail)
        except Exception as e:
            try:
                self.screen.update_log(task_id, f"Failed to fetch log: {str(e)[:100]}")
            except Exception:
                pass

    async def _load_resource_timeline(self):
        """Build a 24-hour pool usage timeline from recent task instances."""
        from datetime import datetime, timezone, timedelta
        try:
            client = self._client
            if not client:
                return

            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=24)
            cutoff_str = cutoff.isoformat()

            # 2 API calls instead of 200+
            ti_result = await client.get_all_task_instances(
                end_date_gte=cutoff_str, limit=500
            )
            pools_result = await client.get_pools()

            pool_capacity = {p.name: p.slots for p in pools_result.pools}
            pool_hours: dict = {}
            consumers: dict = {}

            for ti in ti_result.task_instances:
                if not ti.start_date:
                    continue
                end = ti.end_date or now
                pool = ti.pool or "default_pool"
                duration_mins = (end - ti.start_date).total_seconds() / 60

                # Track consumers
                key = f"{ti.dag_id}:{pool}"
                if key not in consumers:
                    consumers[key] = {"dag_id": ti.dag_id, "slot_minutes": 0, "pool": pool}
                consumers[key]["slot_minutes"] += duration_mins

                # Map to hourly buckets
                if pool not in pool_hours:
                    pool_hours[pool] = {}
                hours_ago = (now - ti.start_date).total_seconds() / 3600
                hour_offset = min(int(hours_ago), 23)
                if 0 <= hour_offset <= 23:
                    pool_hours[pool][hour_offset] = pool_hours[pool].get(hour_offset, 0) + 1

            top_consumers = sorted(consumers.values(), key=lambda x: x["slot_minutes"], reverse=True)

            self.screen.update_timeline(pool_hours, pool_capacity, top_consumers)
        except Exception as e:
            self._flash_error(f"Timeline load failed: {str(e)[:80]}")

    async def _load_watchlist(self):
        """Load status for all bookmarked DAGs."""
        from airterm.metrics.aggregations import compute_duration_stats, compute_success_rate
        try:
            client = self._client
            if not client:
                return

            watchlist = self._watchlist
            if not watchlist:
                self.screen.update_watchlist([])
                return

            entries = []
            for dag_id in watchlist:
                try:
                    runs_result = await client.get_dag_runs(dag_id, limit=10)
                    runs = runs_result.dag_runs
                    if not runs:
                        entries.append({"dag_id": dag_id, "state": "no runs"})
                        continue

                    latest = runs[0]
                    state = latest.state.value if latest.state else ""
                    duration = ""
                    duration_secs = 0.0
                    if latest.start_date and latest.end_date:
                        duration_secs = (latest.end_date - latest.start_date).total_seconds()
                        duration = f"{int(duration_secs // 60)}m {int(duration_secs % 60)}s"

                    stats = compute_duration_stats(runs)
                    avg = stats.get("avg", 0.0)
                    avg_str = f"{int(avg // 60)}m {int(avg % 60)}s" if avg else ""
                    drift = ""
                    if avg > 0 and duration_secs > 0:
                        pct = ((duration_secs - avg) / avg) * 100
                        sign = "+" if pct > 0 else ""
                        drift = f"{sign}{pct:.0f}%"

                    sr = compute_success_rate(runs) * 100

                    entries.append({
                        "dag_id": dag_id,
                        "state": state,
                        "last_run": str(latest.execution_date)[:16],
                        "duration": duration,
                        "avg_duration": avg_str,
                        "drift": drift,
                        "success_rate": f"{sr:.0f}%",
                    })
                except Exception:
                    entries.append({"dag_id": dag_id, "state": "error"})

            self.screen.update_watchlist(entries)
        except Exception as e:
            self._flash_error(f"Watchlist load failed: {str(e)[:80]}")

    # ── Navigation ───────────────────────────────────────────────────────────

    def action_focus_filter(self):
        try:
            from airterm.widgets.filter_input import FilterInput
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
        self._cancel_watch_on_switch()
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
        if self._auto_refresh_enabled:
            self._stop_watch()
        if self._poller or self._client:
            _asyncio.create_task(self._shutdown())
        else:
            self.exit()

    async def _shutdown(self):
        """Clean shutdown: stop poller, close HTTP client."""
        if self._poller:
            await self._poller.stop_all()
        if self._client:
            await self._client.close()
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
