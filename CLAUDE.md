# Terminair — Claude Code Guide

## What This Is

Terminair is a **read-only** k9s-style TUI for Apache Airflow. It connects to any Airflow instance via the REST API and provides instant navigation across DAGs, runs, tasks, pools, and health — no writes, no log viewer, no browser needed.

## Running Locally

```bash
# Install local dev dependencies
make setup

# Recommended: set password via env var
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin

# Or with interactive prompt
python3 -m terminair --url http://localhost:8080 --user admin
# → Password: ********
```

A local Airflow instance with example DAGs is used for development:
- URL: `http://localhost:8080`
- Credentials: `admin` / `admin`
- `make demo` clones the example Airflow stack into `.demo/airflow-dag-template`, starts Docker, and launches Terminair against it

## Architecture

```
terminair/
  app.py               # TerminairApp (Textual App) — routing, global bindings, screen stack
  cli.py               # Click entry point → resolves credentials → runs TerminairApp
  config.py            # Config / ConnectionSettings model (Pydantic)
  api/
    client.py          # AirflowClient — all REST calls (GET only)
    models.py          # Pydantic models for API responses
    poller.py          # Background polling loop (writes to no shared state)
  screens/
    dags.py             # Main screen - k9s layout with inline header/filter
    dag_detail.py       # DAG run history + metrics panel
    dag_graph.py        # DAG dependency graph with critical path highlighting
    dag_deps.py         # DAG dataset dependency impact view
    task_instances.py   # Task states for a run
    task_history.py     # Cross-run pass/fail pattern
    pools.py            # Pool utilization and contention alerts
    health.py           # Scheduler / metadb health
    broken_summary.py   # Failed runs + import errors summary
    recent_activity.py  # Feed of recent runs
    event_log.py        # Airflow event log
    xcom_viewer.py      # XCom key/value inspector for a task instance
    sla_misses.py       # Running DAGs that have exceeded their P95 duration
    resource_timeline.py # 24h pool slot usage timeline with top consumers
    watchlist.py        # Bookmarked DAGs with status summary
  widgets/
    filter_input.py     # Inline /filter bar
    flash.py            # FlashBar - bottom-dock status widget
    help_overlay.py     # HelpScreen modal overlay
    command_palette.py   # : command palette
    box_plot.py         # ASCII box plot widget
  metrics/
    aggregations.py     # streak, success_rate, duration_stats, drift
    sparkline.py        # compute_sparkline, render_pattern
    critical_path.py     # build_dag_graph, find_critical_path
    error_extract.py     # extract_error, normalize_error, cluster_errors
  themes/
    dark.py             # DARK_CSS - global Textual CSS
    light.py            # LIGHT_CSS - alternate theme
  tests/
    test_read_only.py    # Ensures no write methods exist on AirflowClient
    test_metrics.py      # Sparkline / aggregation unit tests
    test_failure_heatmap.py
    test_flash.py        # Flash widget unit tests
    test_config.py       # Config loading and credential handling tests
    test_command_palette.py
    test_event_log_loader.py
```

## Screen Stack Model

The app uses Textual's `push_screen` / `pop_screen`:

- `stack[0]` - base App compose screen (CommandPalette + refresh status + FlashBar)
- `stack[1]` - **DagsScreen** (root navigation level)
- `stack[2+]` - detail screens pushed on drill-in

`action_back` only pops when `len(stack) > 2`, keeping DagsScreen as the floor.

Number-key switches use `_switch_to(screen_name)`, which pops to the floor before pushing, keeping the stack bounded.

Each pushed Screen owns its own chrome: header, DataTable, optional filter bar, and footer.

## Key Bindings

| Key | Action |
|-----|--------|
| `1` | Errors view |
| `2` | Pools |
| `3` | Health |
| `4` | SLA misses |
| `5` | Resource timeline |
| `0` | Watchlist |
| `Enter` | Drill into selected DAG → DAG detail |
| `h` | Task history |
| `d` | Dataset dependencies |
| `x` | XCom viewer |
| `b` | Bookmark / unbookmark DAG |
| `w` | Toggle wrapped columns in the DAG table |
| `/` | Open filter bar on the DAGs screen |
| `Esc` | Back / clear filter |
| `r` | Refresh current screen |
| `:` | Command palette |
| `q` | Quit |
| `Ctrl+C` | Quit immediately |

## Key Design Rules

1. **Strictly read-only** — `AirflowClient` only has `GET` methods. The test `test_read_only.py` enforces this.
2. **k9s interaction model** — Key hints always visible in the header; no separate help screen needed.
3. **Filter bar** — `/` opens an inline filter bar. Typing filters the DataTable live. `Enter` closes the bar but keeps the filter active. `Esc` clears the filter and closes the bar.
4. **Async load pattern** — All data loading is async. Screen actions call `asyncio.create_task(self._load_*())` after `_switch_to()` or `push_screen()`. Never call async load functions directly without `create_task`.
5. **Error feedback** — Never use bare `except Exception: pass` in loaders. Catch with `except Exception as e:` and call `self._flash_error(f"<context>: {str(e)[:80]}")`. The `FlashBar` widget auto-clears after 8 seconds.
6. **Screen switching** — Use `self._switch_to(screen_name)` for number-key navigation. Only use `push_screen()` directly for drill-in actions.

## Adding a New Screen

1. Create `terminair/screens/my_screen.py` - subclass `Screen`, set `SCROLLABLE = False`, compose with a header, a DataTable with border-title, optional `FilterInput`, and a footer Static.
2. Register in `app.py` `SCREENS` dict.
3. Add a number-key binding and a `action_switch_my_screen()` method that calls `self._switch_to("my_screen")` then `_asyncio.create_task(self._load_my_screen())`.
4. Add `_load_my_screen()` async method in `app.py` — wrap the body in `try/except Exception as e: self._flash_error(...)`.
5. Add the screen's interval to the app refresh cadence if it needs polling.

## Tests

```bash
python3 -m pytest terminair/tests/ -v
```

Tests are in `terminair/tests/`. The `conftest.py` provides fixtures for config and mock API data.
