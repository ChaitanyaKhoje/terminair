# Terminair Agent Instructions

## Quick Commands

```bash
# Install local dev dependencies
make setup

# Start the demo Airflow stack and run Terminair against it
make demo

# Start/stop Airflow only
make airflow-up
make airflow-down

# Run the app
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin

# Run tests
python3 -m pytest terminair/tests/ -v

# CLI help
python3 -m terminair --help
python3 -m terminair --version
```

## Key Architecture

- **Entry point**: `terminair.cli:main` (via `python3 -m terminair`)
- **App class**: `terminair.app.TerminairApp` (Textual App subclass)
- **API client**: `terminair.api.client.AirflowClient` (GET only - no write methods)
- **Config**: `terminair.config.Config` plus `merge_configs()` for CLI and file overrides
- **Main screens**: `dags`, `broken_summary`, `pools`, `health`, `sla_misses`, `resource_timeline`, `watchlist`, `recent_activity`, `task_history`, `task_instances`, `dag_deps`, `xcom_viewer`

## Critical Constraints

1. **Read-only enforcement**: API client has NO POST/PATCH/DELETE methods. Test at `terminair/tests/test_read_only.py`.

2. **Textual 8.x API quirks** (not obvious from docs):
   - `Static(id=...)` not valid - use `Static(); widget.id = "foo"` after creation
   - `widget.display = False` not `show=False` for hiding
   - Screens registered via `SCREENS = {"name": ScreenClass}` dict on App, not `name=` argument
   - `httpx.Timeout(30.0)` not positional args

3. **Python version**: Uses Python 3.11+ syntax but runs on 3.9+ with `from __future__ import annotations`

## Project Structure

```
terminair/
├── api/            # HTTP client, models, poller, auth
├── metrics/        # aggregations, critical path, sparkline, error extraction
├── screens/        # Textual Screen classes
├── themes/         # CSS themes
├── widgets/        # reusable UI components
└── tests/         # pytest modules
```

## Important Files

- `pyproject.toml` - dependencies, CLI entry, Ruff/mypy config
- `terminair/config.py` - config loading, CLI merging
- `README.md` - user-facing run, install, and navigation docs

## Dependencies

Core: textual, httpx, pydantic, click, pyyaml, rich
Dev: pytest, ruff (lint), mypy

## Common Issues Fixed

- Config merging bug: use `settings_dict = settings.model_dump(); Settings(**settings_dict)`
- CSS variables: must be defined with `$name: #hex;` before use
- Screen access: use `SCREENS` dict, then `push_screen("name")`
