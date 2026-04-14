# AirTerm — Claude Code Guide

## What This Is

AirTerm is a **read-only** k9s-style TUI for Apache Airflow. It connects to any Airflow instance via the REST API and provides instant navigation across DAGs, runs, tasks, pools, and health — no writes, no log viewer, no browser needed.

## Running Locally

```bash
python3 -m airterm --url http://localhost:8080 --user admin --password admin
```

A local Airflow instance with example DAGs is used for development:
- URL: `http://localhost:8080`
- Credentials: `admin` / `admin`

## Architecture

```
airterm/
  app.py               # AirTermApp (Textual App) — routing, global bindings, screen stack
  cli.py               # Argparse entry point → builds Config → runs AirTermApp
  config.py            # Config / ConnectionSettings model
  state.py             # Shared state (cached DAGs etc)
  api/
    client.py          # AirflowClient — all REST calls (GET only)
    models.py          # Pydantic models for API responses
    poller.py          # Background polling loop
  screens/
    dags.py            # ★ Main screen — k9s layout with inline header/filter
    dag_detail.py      # DAG run history + metrics panel
    dag_runs.py        # Run list
    dag_graph.py       # DAG dependency graph
    task_instances.py  # Task states for a run
    task_history.py    # Cross-run pass/fail pattern
    pools.py           # Pool utilization
    health.py          # Scheduler / metadb health
    import_errors.py   # DAG parse errors
    recent_activity.py # Feed of recent runs
    event_log.py       # Airflow event log
  widgets/
    filter_input.py    # Inline /filter bar (lives inside each screen that needs it)
    help_overlay.py    # HelpScreen ModalScreen (currently unused — hints in header)
    command_palette.py # : command palette
    header_bar.py      # (legacy, not used in main screens)
    footer_bar.py      # (legacy, not used in main screens)
  themes/
    dark.py            # DARK_CSS — global Textual CSS
  tests/
    test_read_only.py  # Ensures no write methods exist on AirflowClient
    test_metrics.py    # Sparkline / aggregation unit tests
```

## Screen Stack Model

The app uses Textual's `push_screen` / `pop_screen`:

- `stack[0]` — base App compose screen (minimal, just CommandPalette widget)
- `stack[1]` — **DagsScreen** (root navigation level — never popped)
- `stack[2+]` — detail screens pushed on drill-in

`action_back` only pops when `len(stack) > 2`, keeping DagsScreen as the floor.

Each pushed Screen owns its own chrome: the header (3-line info + key hints), the DataTable with border-title, the filter bar, and the footer `<screen_name>`.

## Key Design Rules

1. **Strictly read-only** — `AirflowClient` only has `GET` methods. The test `test_read_only.py` enforces this.
2. **No log viewer** — Error summaries are extracted from the last few lines of failed task logs (single API call). Full log viewing is out of scope.
3. **k9s interaction model** — Key hints always visible in the header; no separate help screen needed.
4. **Filter bar** — `/` opens an inline filter bar. Typing filters the DataTable live. `Enter` closes the bar but keeps the filter active. `Esc` clears the filter and closes the bar.

## Adding a New Screen

1. Create `airterm/screens/my_screen.py` — subclass `Screen`, set `SCROLLABLE = False`, compose with a 3-line header Static, a DataTable with border-title, FilterInput, and a footer Static.
2. Register in `app.py` `SCREENS` dict.
3. Add a `push_screen("my_screen")` action and a number-key binding.

## Tests

```bash
python3 -m pytest airterm/tests/ -v
```

Tests are in `airterm/tests/`. The `conftest.py` provides a mock `AirflowClient`.
