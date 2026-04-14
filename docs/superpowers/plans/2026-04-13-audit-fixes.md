# AirTerm Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all P0/P1/P2 issues from the security & architecture audit, adopting k9s patterns where applicable.

**Architecture:** Work bottom-up: fix bugs first (P0), then remove dead code and fix structural issues (P1), then improve security and UX (P2). Each task is independently committable. The flash message system is the foundation for replacing silent error swallowing, so it comes first.

**Tech Stack:** Python 3.11, Textual TUI framework, httpx async HTTP, Pydantic v2, Click CLI

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `airterm/widgets/flash.py` | Flash message widget (k9s-inspired status feedback) |
| Create | `airterm/tests/test_flash.py` | Flash widget unit tests |
| Create | `airterm/tests/test_config.py` | Config/auth validation tests |
| Create | `airterm/tests/test_command_palette.py` | Command palette input validation tests |
| Modify | `airterm/app.py` | Error handling, screen stack, client cleanup, refresh intervals |
| Modify | `airterm/cli.py` | Env var + interactive password support |
| Modify | `airterm/config.py` | Remove dead `from_env()`, fix empty-token fallback |
| Modify | `airterm/api/poller.py` | Remove StateManager dependency |
| Modify | `airterm/api/client.py` | Add bulk task instances endpoint |
| Modify | `airterm/widgets/command_palette.py` | Typed argument validation |
| Modify | `airterm/screens/dags.py` | Mount flash widget |
| Modify | `README.md` | Auth setup documentation |
| Delete | `airterm/state.py` | Dead StateManager (nothing reads from it) |
| Delete | `airterm/screens/dag_runs.py` | Orphaned screen (no binding, no loader) |
| Delete | `airterm/widgets/header_bar.py` | Legacy, never imported |
| Delete | `airterm/widgets/footer_bar.py` | Legacy, never imported |
| Delete | `airterm/widgets/breadcrumb.py` | Never imported |
| Delete | `airterm/widgets/settings_drawer.py` | Never imported |
| Delete | `airterm/widgets/confirm_modal.py` | Never imported |
| Delete | `airterm/widgets/status_bar.py` | Never imported |

---

### Task 1: Fix EventLog field name bug (P0)

**Files:**
- Modify: `airterm/app.py:407-423`

- [ ] **Step 1: Write the failing test**

Create `airterm/tests/test_event_log_loader.py`:

```python
"""Test that event log loader uses correct model field names."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from airterm.api.models import EventLog, EventLogList


def test_event_log_model_fields():
    """Verify the EventLog model uses event_timestamp and event_type, not when/event."""
    log = EventLog(
        event_log_id=1,
        event_timestamp=datetime(2026, 4, 13, 12, 0, 0),
        event_type="dag_started",
        dag_id="test_dag",
        owner="admin",
    )
    assert log.event_timestamp == datetime(2026, 4, 13, 12, 0, 0)
    assert log.event_type == "dag_started"
    assert not hasattr(log, "when")
    assert not hasattr(log, "event")
```

- [ ] **Step 2: Run test to verify it passes (model is correct, app.py is wrong)**

Run: `python3 -m pytest airterm/tests/test_event_log_loader.py -v`
Expected: PASS (the model is fine; the bug is in app.py's usage)

- [ ] **Step 3: Fix the field references in app.py**

In `airterm/app.py`, replace the `_load_event_logs` method body (lines 407-423):

```python
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
        except Exception:
            pass
```

Change `log.when` → `log.event_timestamp` and `log.event` → `log.event_type`.

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add airterm/app.py airterm/tests/test_event_log_loader.py
git commit -m "fix: use correct EventLog field names (event_timestamp, event_type)"
```

---

### Task 2: Create flash message widget (P0 foundation)

**Files:**
- Create: `airterm/widgets/flash.py`
- Create: `airterm/tests/test_flash.py`

- [ ] **Step 1: Write tests for the flash widget**

Create `airterm/tests/test_flash.py`:

```python
"""Tests for flash message widget."""

from airterm.widgets.flash import FlashMessage, FlashLevel


def test_flash_message_creation():
    msg = FlashMessage("test error", FlashLevel.ERROR)
    assert msg.text == "test error"
    assert msg.level == FlashLevel.ERROR


def test_flash_message_default_level():
    msg = FlashMessage("info message")
    assert msg.level == FlashLevel.INFO


def test_flash_level_values():
    assert FlashLevel.INFO.value == "info"
    assert FlashLevel.WARN.value == "warn"
    assert FlashLevel.ERROR.value == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest airterm/tests/test_flash.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the flash widget**

Create `airterm/widgets/flash.py`:

```python
"""Flash message widget — k9s-inspired status feedback."""

from enum import Enum
from dataclasses import dataclass, field
from time import monotonic

from textual.widgets import Static


class FlashLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class FlashMessage:
    text: str
    level: FlashLevel = FlashLevel.INFO
    created_at: float = field(default_factory=monotonic)


# Color map per level (Dracula theme)
_COLORS = {
    FlashLevel.INFO: "cyan",
    FlashLevel.WARN: "yellow",
    FlashLevel.ERROR: "red",
}

_ICONS = {
    FlashLevel.INFO: "i",
    FlashLevel.WARN: "!",
    FlashLevel.ERROR: "x",
}


class FlashBar(Static):
    """A single-line status bar that shows the latest flash message."""

    DEFAULT_CSS = """
    FlashBar {
        height: 1;
        dock: bottom;
        background: #282a36;
        color: #f8f8f2;
        padding: 0 1;
    }
    """

    def __init__(self):
        super().__init__("")
        self._current: FlashMessage | None = None
        self._clear_timer = None

    def flash(self, text: str, level: FlashLevel = FlashLevel.INFO, duration: float = 6.0):
        """Show a flash message that auto-clears after duration seconds."""
        self._current = FlashMessage(text, level)
        color = _COLORS[level]
        icon = _ICONS[level]
        self.update(f"[{color}][{icon}] {text}[/{color}]")

        # Cancel previous timer
        if self._clear_timer is not None:
            self._clear_timer.stop()
        self._clear_timer = self.set_timer(duration, self._clear)

    def flash_error(self, text: str, duration: float = 8.0):
        """Convenience for error-level flash."""
        self.flash(text, FlashLevel.ERROR, duration)

    def flash_warn(self, text: str, duration: float = 6.0):
        """Convenience for warn-level flash."""
        self.flash(text, FlashLevel.WARN, duration)

    def _clear(self):
        self._current = None
        self.update("")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest airterm/tests/test_flash.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add airterm/widgets/flash.py airterm/tests/test_flash.py
git commit -m "feat: add FlashBar widget for user-visible error feedback"
```

---

### Task 3: Wire flash bar into app and replace silent error swallowing (P0)

**Files:**
- Modify: `airterm/app.py`

- [ ] **Step 1: Add FlashBar to app compose and add a helper method**

In `airterm/app.py`, add the import at the top:

```python
from airterm.widgets.flash import FlashBar
```

Replace the `compose` method:

```python
    def compose(self) -> ComposeResult:
        yield CommandPalette()
        yield FlashBar()
```

Add a helper method to `AirTermApp`:

```python
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
```

- [ ] **Step 2: Replace all `except Exception: pass` blocks with flash feedback**

In every `_load_*` method in `app.py`, replace:
```python
        except Exception:
            pass
```
with:
```python
        except Exception as e:
            self._flash_error(f"<screen>: {str(e)[:80]}")
```

The full list of methods to update (each gets a descriptive prefix):

| Method | Flash prefix |
|--------|-------------|
| `_load_dags` | `"DAGs load failed"` |
| `_load_recent_activity` | `"Recent activity load failed"` |
| `_load_pools` | `"Pools load failed"` |
| `_load_health` | `"Health load failed"` |
| `_load_import_errors` | `"Import errors load failed"` |
| `_load_event_logs` | `"Event logs load failed"` |
| `_load_sla_misses` | `"SLA check failed"` |
| `_load_xcoms` | `"XCom load failed"` |
| `_load_dag_graph` | `"Graph load failed"` |
| `_load_task_history` | `"Task history load failed"` |
| `_load_dag_detail` | `"DAG detail load failed"` |
| `_load_dag_deps` | `"Dependencies load failed"` |
| `_load_task_log` | (already has specific error handling — keep the existing inner try, add flash to outer) |
| `_load_resource_timeline` | `"Timeline load failed"` |
| `_load_watchlist` | `"Watchlist load failed"` |

Example transformation for `_load_pools`:

```python
    async def _load_pools(self):
        try:
            client = self._client
            if not client:
                return
            pools_result = await client.get_pools()
            self.screen.update_pools(pools_result.pools)
        except Exception as e:
            self._flash_error(f"Pools load failed: {str(e)[:80]}")
```

Also replace the `except Exception: pass` in `_refresh_current_screen` (line 174):

```python
            except Exception as e:
                self._flash_error(f"Refresh failed: {str(e)[:80]}")
```

- [ ] **Step 3: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add airterm/app.py
git commit -m "feat: replace silent error swallowing with flash bar messages"
```

---

### Task 4: Delete dead StateManager and simplify Poller (P1)

**Files:**
- Delete: `airterm/state.py`
- Modify: `airterm/api/poller.py`

- [ ] **Step 1: Verify StateManager is not read anywhere except poller**

Run: `grep -rn "get_state\|from airterm.state\|import state" airterm/ --include="*.py"`

Expected: Only hits in `state.py` and `poller.py`.

- [ ] **Step 2: Simplify the Poller to remove state writes**

Replace `airterm/api/poller.py` with:

```python
"""Background poller for Airflow API data."""

import asyncio
from typing import Callable, Optional

from airterm.api.client import AirflowClient


class Poller:
    """Background poller for Airflow API data."""

    def __init__(self, client: AirflowClient):
        self._client = client
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def start_polling(
        self,
        resource: str,
        interval: float,
        callback: Optional[Callable] = None,
        **params,
    ):
        """Start polling a resource. Replaces existing poll for same resource."""
        await self.stop_polling(resource)
        self._running = True
        task = asyncio.create_task(self._poll_loop(resource, interval, callback, **params))
        self._tasks[resource] = task

    async def stop_polling(self, resource: str):
        """Stop polling a specific resource."""
        if resource in self._tasks:
            self._tasks[resource].cancel()
            try:
                await self._tasks[resource]
            except asyncio.CancelledError:
                pass
            del self._tasks[resource]

    async def stop_all(self):
        """Stop all active polls."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    async def _poll_loop(
        self,
        resource: str,
        interval: float,
        callback: Optional[Callable],
        **params,
    ):
        while self._running:
            try:
                data = await self._poll_once(resource, **params)
                if callback and data is not None:
                    callback(data)
            except Exception:
                pass  # Flash will be handled by the app-level refresh
            await asyncio.sleep(interval)

    async def _poll_once(self, resource: str, **params):
        if resource == "dags":
            return await self._client.get_dags(**params)
        elif resource == "pools":
            return await self._client.get_pools()
        elif resource == "health":
            return await self._client.get_health()
        return None


_default_poller: Optional[Poller] = None


def get_poller() -> Optional[Poller]:
    return _default_poller


def set_poller(poller: Poller):
    global _default_poller
    _default_poller = poller
```

- [ ] **Step 3: Delete `airterm/state.py`**

```bash
rm airterm/state.py
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass (nothing imports state.py)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove dead StateManager, simplify Poller"
```

---

### Task 5: Close httpx client on app exit (P1)

**Files:**
- Modify: `airterm/app.py`

- [ ] **Step 1: Add cleanup to action_quit**

In `airterm/app.py`, replace `action_quit`:

```python
    def action_quit(self):
        if self._auto_refresh_enabled:
            self._stop_watch()
        if self._poller:
            asyncio.create_task(self._shutdown())
        else:
            self.exit()

    async def _shutdown(self):
        """Clean shutdown: stop poller, close HTTP client."""
        if self._poller:
            await self._poller.stop_all()
        if self._client:
            await self._client.close()
        self.exit()
```

Also add the import at the top if not already present:

```python
import asyncio as _asyncio
```

(Already exists — just use `_asyncio.create_task`.)

Adjust to use `_asyncio`:

```python
    def action_quit(self):
        if self._auto_refresh_enabled:
            self._stop_watch()
        if self._poller or self._client:
            _asyncio.create_task(self._shutdown())
        else:
            self.exit()
```

- [ ] **Step 2: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add airterm/app.py
git commit -m "fix: close httpx client and stop poller on app exit"
```

---

### Task 6: Fix screen stack growth (P1)

**Files:**
- Modify: `airterm/app.py`

- [ ] **Step 1: Add a `_switch_to` helper that pops to floor first**

In `airterm/app.py`, add:

```python
    def _switch_to(self, screen_name: str):
        """Pop to DagsScreen floor, then push the target screen."""
        self._cancel_watch_on_switch()
        while len(self.screen_stack) > 2:
            self.pop_screen()
        self.push_screen(screen_name)
```

- [ ] **Step 2: Replace all number-key switch actions to use `_switch_to`**

```python
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
```

- [ ] **Step 3: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add airterm/app.py
git commit -m "fix: pop screen stack to floor before pushing on number-key switches"
```

---

### Task 7: Fix Resource Timeline N+1 API calls (P1)

**Files:**
- Modify: `airterm/api/client.py`
- Modify: `airterm/app.py`

- [ ] **Step 1: Add a bulk task instances endpoint to the client**

In `airterm/api/client.py`, add a new method:

```python
    async def get_all_task_instances(
        self,
        end_date_gte: Optional[str] = None,
        end_date_lte: Optional[str] = None,
        limit: int = 500,
    ) -> models.TaskInstanceList:
        """Fetch task instances across all DAGs (bulk endpoint)."""
        params: Dict[str, str] = {"limit": str(limit)}
        if end_date_gte:
            params["end_date_gte"] = end_date_gte
        if end_date_lte:
            params["end_date_lte"] = end_date_lte
        resp = await self._client.get(
            "/api/v1/dags/-/dagRuns/-/taskInstances",
            params=params,
        )
        resp.raise_for_status()
        return models.TaskInstanceList(**resp.json())
```

- [ ] **Step 2: Rewrite `_load_resource_timeline` to use the bulk endpoint**

In `airterm/app.py`, replace `_load_resource_timeline` (lines 667-726):

```python
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
```

- [ ] **Step 3: Verify read-only contract still holds**

Run: `python3 -m pytest airterm/tests/test_read_only.py -v`
Expected: PASS

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add airterm/api/client.py airterm/app.py
git commit -m "perf: replace N+1 timeline API calls with bulk task instances endpoint"
```

---

### Task 8: Add env var and interactive prompt for password (P2)

**Files:**
- Modify: `airterm/cli.py`
- Create: `airterm/tests/test_config.py`

- [ ] **Step 1: Write tests for env var and fallback behavior**

Create `airterm/tests/test_config.py`:

```python
"""Tests for config loading and credential handling."""

import os
import pytest
from unittest.mock import patch

from airterm.config import CLIConfig, Config, Connection, ConnectionAuthBasic, Settings, merge_configs


def test_merge_config_with_basic_auth():
    file_config = Config()
    cli_config = CLIConfig(url="http://localhost:8080", user="admin", password="secret")
    result = merge_configs(file_config, cli_config)
    conn = result.connections["default"]
    assert conn.auth.username == "admin"
    assert conn.auth.password == "secret"


def test_merge_config_url_without_creds_raises():
    """Providing --url without --user/--password should raise, not silently send empty token."""
    file_config = Config()
    cli_config = CLIConfig(url="http://localhost:8080")
    with pytest.raises(ValueError, match="credentials"):
        merge_configs(file_config, cli_config)


def test_settings_has_no_from_env():
    """from_env was dead code referencing nonexistent api_token field — verify it's removed."""
    assert not hasattr(Settings, "from_env")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest airterm/tests/test_config.py -v`
Expected: `test_merge_config_url_without_creds_raises` FAILS (currently creates empty token), `test_settings_has_no_from_env` FAILS

- [ ] **Step 3: Fix config.py — remove dead `from_env`, fix empty-token fallback**

In `airterm/config.py`, remove the `from_env` classmethod from `Settings` (lines 39-42):

Delete:
```python
    @classmethod
    def from_env(cls) -> "Settings":
        api_token = os.environ.get("AIRFLOW_API_TOKEN")
        return cls(api_token=api_token)
```

In `merge_configs`, replace the `else` branch (lines 107-111):

```python
        else:
            raise ValueError(
                "URL provided without credentials. Use --user/--password, "
                "set AIRTERM_PASSWORD env var, or configure a connection in config.yaml."
            )
```

- [ ] **Step 4: Add env var and interactive prompt support to cli.py**

Replace `airterm/cli.py`:

```python
"""CLI entrypoint for AirTerm."""

import os
from pathlib import Path

import click

from airterm.app import AirTermApp
from airterm.config import CLIConfig, Config, merge_configs


@click.command()
@click.option("--url", help="Airflow API URL")
@click.option("--user", help="Username for basic auth")
@click.option("--password", help="Password for basic auth (prefer AIRTERM_PASSWORD env var)")
@click.option("--ctx", help="Connection context name")
@click.option("--config", type=click.Path(path_type=Path), help="Config file path")
@click.option("--dag", help="Jump to specific DAG on startup")
@click.option("--refresh", type=int, help="Refresh interval in seconds")
@click.option("--version", is_flag=True, help="Show version")
def main(
    url,
    user,
    password,
    ctx,
    config,
    dag,
    refresh,
    version,
):
    """AirTerm - A k9s-style TUI for Apache Airflow."""
    if version:
        click.echo("airterm version 0.1.0")
        return

    # Resolve password: CLI arg > env var > interactive prompt
    if url and user and not password:
        password = os.environ.get("AIRTERM_PASSWORD")
        if not password:
            password = click.prompt("Password", hide_input=True)

    cli_config = CLIConfig(
        url=url,
        user=user,
        password=password,
        ctx=ctx,
        config_path=config,
        dag=dag,
        refresh=refresh,
    )

    file_config = Config.load(cli_config.config_path)

    try:
        full_config = merge_configs(file_config, cli_config)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    app = AirTermApp(full_config)
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest airterm/tests/test_config.py -v`
Expected: All 3 pass

- [ ] **Step 6: Commit**

```bash
git add airterm/cli.py airterm/config.py airterm/tests/test_config.py
git commit -m "feat: env var + interactive prompt for password, remove dead Settings.from_env"
```

---

### Task 9: Delete dead code — orphaned screen and unused widgets (P2)

**Files:**
- Delete: `airterm/screens/dag_runs.py`
- Delete: `airterm/widgets/header_bar.py`
- Delete: `airterm/widgets/footer_bar.py`
- Delete: `airterm/widgets/breadcrumb.py`
- Delete: `airterm/widgets/settings_drawer.py`
- Delete: `airterm/widgets/confirm_modal.py`
- Delete: `airterm/widgets/status_bar.py`
- Modify: `airterm/app.py` (remove DagRunsScreen import and SCREENS entry)

- [ ] **Step 1: Verify none of the widgets are imported anywhere**

Run:
```bash
grep -rn "from airterm.widgets.header_bar\|from airterm.widgets.footer_bar\|from airterm.widgets.breadcrumb\|from airterm.widgets.settings_drawer\|from airterm.widgets.confirm_modal\|from airterm.widgets.status_bar" airterm/ --include="*.py"
```

Expected: No matches.

Run:
```bash
grep -rn "DagRunsScreen\|dag_runs" airterm/ --include="*.py" | grep -v "dag_runs.py"
```

Expected: Only hits in `app.py` import and SCREENS dict.

- [ ] **Step 2: Remove DagRunsScreen from app.py**

In `airterm/app.py`, delete the import line:
```python
from airterm.screens.dag_runs import DagRunsScreen
```

Remove from the `SCREENS` dict:
```python
        "dag_runs": DagRunsScreen,
```

- [ ] **Step 3: Delete the files**

```bash
rm airterm/screens/dag_runs.py
rm airterm/widgets/header_bar.py
rm airterm/widgets/footer_bar.py
rm airterm/widgets/breadcrumb.py
rm airterm/widgets/settings_drawer.py
rm airterm/widgets/confirm_modal.py
rm airterm/widgets/status_bar.py
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove orphaned DagRunsScreen and 6 unused widgets"
```

---

### Task 10: Validate command palette arguments (P2)

**Files:**
- Modify: `airterm/widgets/command_palette.py`
- Create: `airterm/tests/test_command_palette.py`

- [ ] **Step 1: Write tests**

Create `airterm/tests/test_command_palette.py`:

```python
"""Tests for command palette argument validation."""

from airterm.widgets.command_palette import CommandExecutor


def test_parse_empty():
    cmd, args = CommandExecutor.parse("")
    assert cmd is None
    assert args == []


def test_parse_simple_command():
    cmd, args = CommandExecutor.parse("pools")
    assert cmd == "pools"
    assert args == []


def test_parse_command_with_arg():
    cmd, args = CommandExecutor.parse("dag my_dag_id")
    assert cmd == "dag"
    assert args == ["my_dag_id"]


def test_unknown_command_rejected():
    assert CommandExecutor.validate("unknown_cmd", []) is False


def test_known_command_no_args_valid():
    assert CommandExecutor.validate("pools", []) is True


def test_dag_command_requires_arg():
    assert CommandExecutor.validate("dag", []) is False
    assert CommandExecutor.validate("dag", ["my_dag"]) is True


def test_ctx_command_requires_arg():
    assert CommandExecutor.validate("ctx", []) is False
    assert CommandExecutor.validate("ctx", ["prod"]) is True


def test_no_arg_commands_reject_extra_args():
    assert CommandExecutor.validate("pools", ["extra"]) is False
    assert CommandExecutor.validate("health", ["extra"]) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest airterm/tests/test_command_palette.py -v`
Expected: FAIL (`validate` doesn't exist yet)

- [ ] **Step 3: Add validation to CommandExecutor**

Replace `airterm/widgets/command_palette.py`:

```python
"""Command palette widget."""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input


class CommandPalette(Widget):
    CSS = """
    CommandPalette {
        dock: top;
        height: 3;
        background: $panel;
        border-bottom: solid $accent;
    }

    CommandPalette Input {
        background: $surface;
        color: $text;
    }

    .hint {
        color: $text-muted;
    }
    """

    def __init__(self):
        super().__init__()
        self.display = False

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder=":dag <name> :pools :health :ctx <name> :filter :export", id="cmd-input"
        )

    def show(self):
        self.display = True
        self.query_one("#cmd-input").focus()

    def hide(self):
        self.display = False

    def on_input_submitted(self, event: Input.Submitted):
        self.hide()
        if event.value:
            self.app.action_execute_command(event.value)


class CommandExecutor:
    """Parses and executes command palette commands."""

    COMMANDS = {
        "dag": "jump_to_dag",
        "pools": "switch_pools",
        "health": "switch_health",
        "errors": "switch_errors",
        "recent": "switch_recent",
        "ctx": "switch_connection",
        "filter": "apply_filter",
        "export": "export_data",
        "set": "set_option",
        "theme": "switch_theme",
    }

    # Commands that require exactly one argument
    _REQUIRES_ARG = {"dag", "ctx", "theme"}
    # Commands that take no arguments
    _NO_ARGS = {"pools", "health", "errors", "recent"}
    # Commands that take optional/variable args
    _OPTIONAL_ARGS = {"filter", "export", "set"}

    @classmethod
    def parse(cls, cmd: str) -> tuple:
        parts = cmd.strip().split()
        if not parts:
            return None, []
        return parts[0], parts[1:]

    @classmethod
    def validate(cls, cmd_name: str, args: list) -> bool:
        """Validate command name and argument count."""
        if cmd_name not in cls.COMMANDS:
            return False
        if cmd_name in cls._REQUIRES_ARG and len(args) != 1:
            return False
        if cmd_name in cls._NO_ARGS and len(args) != 0:
            return False
        return True

    @classmethod
    def execute(cls, app, cmd: str):
        cmd_name, args = cls.parse(cmd)
        if not cls.validate(cmd_name, args):
            try:
                from airterm.widgets.flash import FlashBar
                app.query_one(FlashBar).flash_warn(f"Invalid command: {cmd}")
            except Exception:
                pass
            return False

        action = cls.COMMANDS[cmd_name]
        if hasattr(app, f"action_{action}"):
            getattr(app, f"action_{action}")(*args)
            return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest airterm/tests/test_command_palette.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add airterm/widgets/command_palette.py airterm/tests/test_command_palette.py
git commit -m "feat: validate command palette arguments before dispatch"
```

---

### Task 11: Add per-screen refresh intervals with overlap prevention (P2)

**Files:**
- Modify: `airterm/app.py`

- [ ] **Step 1: Add refresh interval configuration and overlap guard**

In `airterm/app.py`, add a class-level dict for per-screen intervals and a guard flag:

```python
    # Per-screen refresh intervals (seconds)
    _SCREEN_REFRESH_INTERVALS = {
        "DagsScreen": 5,
        "RecentActivityScreen": 10,
        "PoolsScreen": 30,
        "HealthScreen": 60,
        "ImportErrorsScreen": 60,
        "SlaMissScreen": 30,
        "DagDetailScreen": 5,
        "ResourceTimelineScreen": 30,
        "WatchlistScreen": 30,
    }
```

Add a guard to `__init__`:

```python
        self._refresh_in_flight = False
```

- [ ] **Step 2: Update `_watch_loop` to use per-screen intervals and prevent overlap**

Replace `_watch_loop`:

```python
    async def _watch_loop(self):
        while self._auto_refresh_enabled:
            screen_id = self.screen.__class__.__name__
            interval = self._SCREEN_REFRESH_INTERVALS.get(
                screen_id, self._config.settings.refresh_interval
            )
            await _asyncio.sleep(interval)
            if not self._auto_refresh_enabled:
                break
            if self._refresh_in_flight:
                continue
            self._refresh_in_flight = True
            try:
                await self._refresh_current_screen()
            except Exception as e:
                self._flash_error(f"Refresh failed: {str(e)[:80]}")
            finally:
                self._refresh_in_flight = False
```

- [ ] **Step 3: Run all tests**

Run: `python3 -m pytest airterm/tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add airterm/app.py
git commit -m "feat: per-screen refresh intervals with overlap prevention"
```

---

### Task 12: Update README with auth setup documentation (P2)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add auth section to README**

In `README.md`, after the `## Quick Start` section (after line 61), add:

```markdown
## Authentication

AirTerm supports three authentication methods:

### Basic Auth (username/password)

```bash
# Option 1: Environment variable (recommended — avoids shell history)
export AIRTERM_PASSWORD=admin
python3 -m airterm --url http://localhost:8080 --user admin

# Option 2: Interactive prompt (password hidden)
python3 -m airterm --url http://localhost:8080 --user admin
# → Password: ********

# Option 3: CLI argument (visible in process list — use only for local dev)
python3 -m airterm --url http://localhost:8080 --user admin --password admin
```

### Token Auth

Use a config file with an environment variable reference for the token:

```yaml
# ~/.airterm/config.yaml
connections:
  production:
    url: https://airflow.company.com
    auth:
      type: token
      token: ${AIRFLOW_PROD_TOKEN}
```

Then:
```bash
export AIRFLOW_PROD_TOKEN=your-bearer-token
python3 -m airterm --ctx production
```

### Airflow API Setup

AirTerm requires the Airflow REST API to be enabled. For Airflow 2.x:

1. Ensure `api` is in your `airflow.cfg`:
   ```ini
   [api]
   auth_backends = airflow.api.auth.backend.basic_auth
   ```

2. For **MWAA** (AWS Managed Airflow): Use a web login token — AirTerm's token auth mode works with the session token from the MWAA CLI.

3. For **Cloud Composer** (GCP): Use `gcloud` to generate an access token:
   ```bash
   export AIRFLOW_PROD_TOKEN=$(gcloud auth print-access-token)
   python3 -m airterm --ctx production
   ```

4. For **Astronomer**: Use the Astronomer API token from the Astro CLI.

> **Security note:** Avoid passing passwords as CLI arguments in shared environments — they are visible in `ps` output and shell history. Use `AIRTERM_PASSWORD` or interactive prompt instead.
```

- [ ] **Step 2: Update the Quick Start to prefer env var**

Replace the Quick Start section (lines 52-61):

```markdown
## Quick Start

**Requires a running Airflow instance.**

```bash
# Recommended: set password via env var
export AIRTERM_PASSWORD=admin
python3 -m airterm --url http://localhost:8080 --user admin

# Named connection from config
python3 -m airterm --ctx production
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add auth setup guide with env var, token, and managed Airflow instructions"
```

---

## Update CLAUDE.md

After all tasks complete, update `CLAUDE.md` to reflect removed files and new patterns:

- [ ] Remove `dag_runs.py` from the architecture tree
- [ ] Remove `header_bar.py`, `footer_bar.py` from widgets listing
- [ ] Add `flash.py` to widgets listing
- [ ] Note the flash error pattern in "Key Design Rules"
- [ ] Update "Adding a New Screen" to mention `_switch_to` helper

---

## Execution Order

Tasks can be done in this exact order (1-12). Tasks 1-3 are the foundation. Tasks 4-7 are independent of each other after Task 3. Tasks 8-12 are independent of each other after Task 3.

Parallelizable groups after Task 3:
- **Group A** (architecture): Tasks 4, 5, 6
- **Group B** (security/cleanup): Tasks 8, 9
- **Group C** (UX polish): Tasks 10, 11, 12
