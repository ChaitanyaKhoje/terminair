# Phase 3: Config + CLI Extension - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 4 (config.py, cli.py, app.py, test_app_demo.py)
**Analogs found:** 4 / 4

## Context: Audit-and-Gap-Fill Phase

Phase 3 is substantially pre-implemented. All CFG requirements except CFG-05 (topbar warning) are complete and tested. This PATTERNS.md focuses on:
1. The one implementation gap: `_build_data_provider` calls `_logger.warning` but not `self._flash_warn()`.
2. The one test gap: no test asserts that `_flash_warn` is called when manifest is configured-but-missing.
3. Concrete code excerpts for the planner to use when writing targeted modifications.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `terminair/config.py` | model/config | transform | self (existing) | exact — already complete |
| `terminair/cli.py` | utility/entrypoint | request-response | self (existing) | exact — already complete |
| `terminair/app.py` | app/bootstrap | event-driven | self (existing) | exact — one-line gap in `_build_data_provider` |
| `terminair/tests/test_app_demo.py` | test | unit | `terminair/tests/test_config.py` | role-match |

---

## Pattern Assignments

### `terminair/app.py` — The One Gap (CFG-05)

**Analog:** `terminair/app.py` itself (self-referential — gap is additive, not structural)

**Current `_build_data_provider` pattern** (lines 91-146):
The method already exists with correct structure. The gap is that each fallback branch logs to `_logger.warning` but does NOT call `self._flash_warn()`. CONTEXT.md requires warnings to appear "in topbar".

**Flash warn helper pattern** (lines 80-85) — already present, copy this call form:
```python
def _flash_warn(self, text: str):
    """Show a warning message in the flash bar."""
    try:
        self.query_one(FlashBar).flash_warn(text)
    except Exception:
        pass
```

**Current fallback branches that need `self._flash_warn()` added** (lines 99-132):

Branch 1 — no dbt config (line 100):
```python
# CURRENT:
_logger.warning("No dbt configuration found — using demo data")
return MockDataProvider()

# AFTER FIX (add flash_warn alongside logger):
_logger.warning("No dbt configuration found — using demo data")
self._flash_warn("No dbt configuration — running demo data")
return MockDataProvider()
```

Branch 2 — manifest missing (lines 106-110):
```python
# CURRENT:
_logger.warning(
    "dbt manifest missing at %s — using demo data",
    manifest_path or "<unset>",
)
return MockDataProvider()

# AFTER FIX:
_logger.warning(
    "dbt manifest missing at %s — using demo data",
    manifest_path or "<unset>",
)
self._flash_warn(f"dbt manifest missing at {manifest_path or '<unset>'} — using demo data")
return MockDataProvider()
```

Branch 3 — data layer error (lines 121-123):
```python
# CURRENT:
_logger.warning("dbt data layer unavailable — using demo data: %s", exc)
return MockDataProvider()

# AFTER FIX:
_logger.warning("dbt data layer unavailable — using demo data: %s", exc)
self._flash_warn(f"dbt data layer unavailable — using demo data")
return MockDataProvider()
```

Branch 4 — Airflow bridge unavailable (lines 131-132):
```python
# CURRENT:
_logger.warning("Airflow bridge unavailable — continuing without it: %s", exc)

# AFTER FIX:
_logger.warning("Airflow bridge unavailable — continuing without it: %s", exc)
self._flash_warn("Airflow bridge unavailable — continuing without it")
```

**Safety constraint:** `_flash_warn` is called from `on_mount` → `get_data_provider()` → `_build_data_provider()`. FlashBar is composed before `on_mount` fires (see `compose()` lines 68-72). The existing `try/except Exception: pass` guard in `_flash_warn` prevents crash if FlashBar is absent.

---

### `terminair/tests/test_app_demo.py` — Test Gap for CFG-05

**Analog:** `terminair/tests/test_config.py` and existing `test_app_demo.py`

**Existing test structure pattern** (lines 1-25 of test_app_demo.py) — follow this exactly:
```python
"""Tests for demo-mode app bootstrap and data provider fallback."""

from __future__ import annotations

from terminair.config import Config


def test_demo_mode_uses_mock_data_provider():
    from terminair.app import TerminairApp
    from terminair.dbt.mock_data import MockDataProvider

    app = TerminairApp(Config(), demo_mode=True)
    provider = app.get_data_provider()

    assert isinstance(provider, MockDataProvider)
```

**New test to add — manifest-configured-but-missing triggers `_flash_warn`:**
```python
def test_manifest_configured_but_missing_calls_flash_warn(tmp_path, monkeypatch):
    from terminair.app import TerminairApp
    from terminair.config import Config, Connection, ConnectionAuthBasic, DbtConfig, Settings
    from terminair.dbt.mock_data import MockDataProvider

    # Set up a config with a manifest_path that does NOT exist on disk
    missing_manifest = tmp_path / "nonexistent_manifest.json"
    file_config = Config(
        connections={
            "default": Connection(
                url="http://localhost:8080",
                auth=ConnectionAuthBasic(username="admin", password="secret"),
                dbt=DbtConfig(manifest_path=missing_manifest),
            )
        },
        settings=Settings(default_connection="default"),
    )

    app = TerminairApp(file_config, demo_mode=False)

    # Track flash_warn calls
    flash_warn_calls = []
    monkeypatch.setattr(app, "_flash_warn", lambda text: flash_warn_calls.append(text))

    provider = app.get_data_provider()

    assert isinstance(provider, MockDataProvider)
    assert len(flash_warn_calls) == 1
    assert "manifest" in flash_warn_calls[0].lower()
```

**Pattern note:** Use `monkeypatch.setattr(app, "_flash_warn", ...)` to intercept the instance method. No mocking frameworks — pytest's `monkeypatch` is the project standard (see test_cli.py lines 23-24).

---

### `terminair/config.py` — Already Complete (CFG-01, CFG-02, CFG-03)

**No changes needed.** Shown for reference — planner must verify current state matches requirements.

**DbtConfig model** (lines 25-30):
```python
class DbtConfig(BaseModel):
    manifest_path: Optional[Path] = None
    run_results_path: Optional[Path] = None
    run_results_previous_path: Optional[Path] = None
    manifest_previous_path: Optional[Path] = None
    dag_names: list[str] = Field(default_factory=list)
```

**SnowflakeConfig model** (lines 33-40):
```python
class SnowflakeConfig(BaseModel):
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    role: str
```

**Connection extension** (lines 48-49):
```python
dbt: Optional[DbtConfig] = None
snowflake: Optional[SnowflakeConfig] = None
```

**merge_configs demo short-circuit** (lines 158-167):
```python
if cli_config.demo:
    settings_dict = file_config.settings.model_dump()
    if cli_config.refresh is not None:
        settings_dict["refresh_interval"] = cli_config.refresh
    settings_dict["default_connection"] = active_conn
    return Config(
        connections=connections,
        settings=Settings(**settings_dict),
        keybindings=file_config.keybindings,
    )
```

**_merge_dbt_config — appends dag_names, does not replace** (lines 138-151):
```python
def _merge_dbt_config(
    base: Optional[DbtConfig],
    cli_config: CLIConfig,
) -> Optional[DbtConfig]:
    merged = base.model_copy(deep=True) if base is not None else DbtConfig()

    if cli_config.manifest_path is not None:
        merged.manifest_path = cli_config.manifest_path
    if cli_config.run_results_path is not None:
        merged.run_results_path = cli_config.run_results_path
    if cli_config.dag_names:
        merged.dag_names.extend(cli_config.dag_names)

    return merged
```

---

### `terminair/cli.py` — Already Complete (CFG-04)

**No changes needed.** Shown for reference.

**Click flag patterns** (lines 18-33):
```python
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    help="Override the dbt manifest path",
)
@click.option(
    "--run-results",
    type=click.Path(path_type=Path),
    help="Override the dbt run_results path",
)
@click.option(
    "--dag",
    multiple=True,
    help="Append a DAG name to the dbt configuration (repeatable)",
)
@click.option("--demo", is_flag=True, help="Run against demo data with no external services")
```

**CLIConfig construction — tuple to list for multiple=True** (lines 64-75):
```python
cli_config = CLIConfig(
    url=url,
    user=user,
    password=password,
    ctx=ctx,
    config_path=config,
    manifest_path=manifest,
    run_results_path=run_results,
    dag_names=list(dag),   # dag is a tuple from multiple=True
    demo=demo,
    refresh=refresh,
)
```

**Demo_mode passed to app** (line 85):
```python
app = TerminairApp(full_config, demo_mode=cli_config.demo)
```

---

## Shared Patterns

### Pydantic v2 Optional Field
**Source:** `terminair/config.py` lines 1, 8, 25-30
**Apply to:** Any new config model fields
```python
# ruff: noqa: UP045, UP007  ← required at top of file for Optional syntax
from typing import Optional
from pydantic import BaseModel, Field

class SomeConfig(BaseModel):
    some_path: Optional[Path] = None
    some_list: list[str] = Field(default_factory=list)
```

### FlashBar Warning Call
**Source:** `terminair/app.py` lines 80-85
**Apply to:** Any code in app.py that needs to surface a warning to the user in the TUI
```python
self._flash_warn("Your message here — keep under 80 chars")
# Always call _flash_warn alongside _logger.warning, not instead of it
_logger.warning("same message for log file: %s", detail)
self._flash_warn(f"same message for TUI: {detail}")
```

### Test Structure (no mocking frameworks)
**Source:** `terminair/tests/test_config.py` and `terminair/tests/test_app_demo.py`
**Apply to:** All new test functions in this phase
```python
# pytest only — no unittest.mock.patch decorators, no MagicMock
# Use monkeypatch for instance attribute patching:
monkeypatch.setattr(obj, "method_name", lambda *a: None)
# Use direct instantiation for model tests:
app = TerminairApp(Config(), demo_mode=True)
```

### Error Handling in App Actions
**Source:** `terminair/app.py` lines 73-85 (`_flash_error`, `_flash_warn`)
**Apply to:** All new fallback branches in `_build_data_provider`
```python
try:
    self.query_one(FlashBar).flash_warn(text)
except Exception:
    pass  # silent — never let flash failure crash the app
```

---

## No Analog Found

All files have analogs in the codebase. No new-from-scratch files are required.

---

## Implementation Work Summary

| Requirement | Status | Work Needed |
|-------------|--------|-------------|
| CFG-01 DbtConfig model | DONE | None — verify only |
| CFG-02 SnowflakeConfig model | DONE | None — verify only |
| CFG-03 Connection extended | DONE | None — verify only |
| CFG-04 CLI flags | DONE | None — verify only |
| CFG-05 topbar warning (implementation) | GAP | Add `self._flash_warn(...)` after each `_logger.warning` in `_build_data_provider` (4 branches, lines ~100, ~106-110, ~121-123, ~131-132) |
| CFG-05 topbar warning (test) | GAP | Add `test_manifest_configured_but_missing_calls_flash_warn` to `test_app_demo.py` |

**Total edits:** 1 file modified (`terminair/app.py`, 4 one-line additions), 1 file extended (`terminair/tests/test_app_demo.py`, 1 new test function ~20 lines).

---

## Metadata

**Analog search scope:** `terminair/` (config.py, cli.py, app.py, widgets/flash.py, tests/)
**Files scanned:** 7
**Pattern extraction date:** 2026-05-15
