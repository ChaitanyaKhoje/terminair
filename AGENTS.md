# AirTerm Agent Instructions

## Quick Commands

```bash
# Run the app
python3 -m airterm --url http://localhost:8080 --user admin --password admin

# Run tests
python3 -m pytest airterm/tests/ -v

# CLI help
python3 -m airterm --help
python3 -m airterm --version
```

## Key Architecture

- **Entry point**: `airterm.cli:main` (via `python3 -m airterm`)
- **App class**: `airterm.app.AirTermApp` (Textual App subclass)
- **API client**: `airterm.api.client.AirflowClient` (GET only - no write methods)

## Critical Constraints

1. **Read-only enforcement**: API client has NO POST/PATCH/DELETE methods. Test at `airterm/tests/test_read_only.py`.

2. **Textual 8.x API quirks** (not obvious from docs):
   - `Static(id=...)` not valid - use `Static(); widget.id = "foo"` after creation
   - `widget.display = False` not `show=False` for hiding
   - Screens registered via `SCREENS = {"name": ScreenClass}` dict on App, not `name=` argument
   - `httpx.Timeout(30.0)` not positional args

3. **Python version**: Uses Python 3.11+ syntax but runs on 3.9+ with `from __future__ import annotations`

## Project Structure

```
airterm/
├── api/           # HTTP client, models, poller
├── metrics/       # aggregations, sparkline, error_extract
├── screens/       # Textual Screen classes
├── widgets/       # reusable UI components
├── themes/        # CSS themes
└── tests/         # 8 tests (all passing)
```

## Important Files

- `airterm_design_plan_v3.md` - implementation spec
- `pyproject.toml` - dependencies, CLI entry, Ruff/mypy config
- `airterm/config.py` - config loading, CLI merging

## Dependencies

Core: textual, httpx, pydantic, click, pyyaml
Dev: pytest, ruff (lint), mypy

## Common Issues Fixed

- Config merging bug: use `settings_dict = settings.model_dump(); Settings(**settings_dict)`
- CSS variables: must be defined with `$name: #hex;` before use
- Screen access: use `SCREENS` dict, then `push_screen("name")`