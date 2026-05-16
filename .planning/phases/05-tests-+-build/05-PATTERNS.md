# Phase 5: Tests + Build - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 4 (2 new test files, 1 modified test file, 1 modified Dockerfile)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `terminair/tests/dbt/test_regression.py` | test | transform | `terminair/tests/dbt/test_regression_and_mock.py` (TestRegressionAnalyzer class) | exact — source file is the origin |
| `terminair/tests/dbt/test_mock_data.py` | test | transform | `terminair/tests/dbt/test_regression_and_mock.py` (TestMockDataProvider class) | exact — source file is the origin |
| `terminair/tests/test_read_only.py` | test | request-response | `terminair/tests/dbt/test_airflow_bridge.py` lines 31-48 | exact — same inspect-based assertion pattern |
| `Dockerfile` | config | request-response | existing `Dockerfile` (self-modification to fix CMD) | self |

---

## Pattern Assignments

### `terminair/tests/dbt/test_regression.py` (test, transform)

**Analog:** `terminair/tests/dbt/test_regression_and_mock.py` — the `TestRegressionAnalyzer` class (lines 13–314) is the direct source. Move it verbatim.

**Imports pattern** (lines 1–11):
```python
"""Tests for RegressionAnalyzer — all 6 signal types and severity thresholds."""

from __future__ import annotations

import pytest

from terminair.dbt.models import Severity
```

**Core test class pattern** (lines 13–314 of source file):
```python
class TestRegressionAnalyzer:
    def test_import(self):
        from terminair.dbt.regression import RegressionAnalyzer  # noqa: F401

    def test_row_drop_warning_threshold(self):
        """delta < -10% but > -30% → WARNING row_drop."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            rows_written=15000,
            rows_previous=20000,
            row_delta_pct=-25.0,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        row_drops = [s for s in signals if s.signal_type == "row_drop"]
        assert len(row_drops) == 1
        assert row_drops[0].severity == Severity.WARNING
```

**New test to add — upstream_schema_change** (no existing test; implement based on regression.py lines 162–189):

```python
def test_upstream_schema_change_warning(self):
    """Upstream dep changed materialization → WARNING upstream_schema_change on consumer."""
    from terminair.dbt.regression import RegressionAnalyzer
    from terminair.dbt.models import ModelState

    # Previous state: upstream uses "view"
    prev_upstream = ModelState(
        node_id="model.p.stg_orders",
        name="stg_orders",
        tag="core",
        status="success",
        dag_id="",
        task_id="",
        materialization="view",      # <— was view
        schema_name="s",
        database_name="d",
        has_upstream_failure=False,
    )
    # Current state: upstream changed to "table"
    curr_upstream = ModelState(
        node_id="model.p.stg_orders",
        name="stg_orders",
        tag="core",
        status="success",
        dag_id="",
        task_id="",
        materialization="table",     # <— now table
        schema_name="s",
        database_name="d",
        has_upstream_failure=False,
    )
    # Consumer model has upstream_deps populated (CRITICAL: must not be empty)
    consumer = ModelState(
        node_id="model.p.fct_orders",
        name="fct_orders",
        tag="core",
        status="success",
        dag_id="",
        task_id="",
        materialization="incremental",
        schema_name="s",
        database_name="d",
        has_upstream_failure=False,
        upstream_deps=["model.p.stg_orders"],  # <— wires the dep
    )
    # Pass both consumer AND upstream as current; prev contains old upstream
    ra = RegressionAnalyzer([consumer, curr_upstream])
    signals = ra.analyze(prev_models=[prev_upstream])
    schema_changes = [s for s in signals if s.signal_type == "upstream_schema_change"]
    assert len(schema_changes) == 1
    assert schema_changes[0].severity == Severity.WARNING
    assert schema_changes[0].node_id == "model.p.fct_orders"
```

**Pitfall to avoid:** `upstream_deps` on the consumer ModelState must list the upstream's `node_id`. If `upstream_deps=[]` (the default), the loop at regression.py line 165 never executes and the signal is never generated.

---

### `terminair/tests/dbt/test_mock_data.py` (test, transform)

**Analog:** `terminair/tests/dbt/test_regression_and_mock.py` — the `TestMockDataProvider` class (lines 317–446) is the direct source. Move it verbatim.

**Imports pattern** (lines 1–8 of new file):
```python
"""Tests for MockDataProvider — tick() transitions, row_delta_pct recomputation, signal coverage."""

from __future__ import annotations

import asyncio
import inspect
```

**Core test class pattern** (lines 317–446 of source file):
```python
class TestMockDataProvider:
    def test_import(self):
        from terminair.dbt.mock_data import MockDataProvider  # noqa: F401

    def test_get_models_returns_10(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        assert len(models) == 10

    def test_tick_transitions_running_to_success_after_4(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        initial_models = asyncio.run(mdp.get_models())
        assert sum(1 for m in initial_models if m.status == "running") == 2

        for _ in range(4):
            mdp.tick()

        models_after = asyncio.run(mdp.get_models())
        running_after = [m for m in models_after if m.status == "running"]
        assert len(running_after) == 1, f"Expected 1 running after 4 ticks, got {len(running_after)}"

    # ... remaining test methods follow the same pattern
```

**Cleanup action:** After creating `test_regression.py` and `test_mock_data.py` with the split content, delete `test_regression_and_mock.py` to prevent pytest collecting duplicate test IDs. Verify with `pytest --collect-only` before and after.

---

### `terminair/tests/test_read_only.py` (test, request-response)

**Analog:** `terminair/tests/dbt/test_airflow_bridge.py` lines 31–48

**Current state** (`test_read_only.py` lines 1–10):
```python
"""Tests to enforce read-only contract.

Phase 5 will extend this file to assert AirflowBridge has no write methods.
"""


def test_placeholder_read_only_contract():
    """Placeholder: read-only contract enforcement to be extended in Phase 5."""
    # AirflowBridge (Phase 2) will be tested here once it exists.
    pass
```

**Pattern to copy from** (`test_airflow_bridge.py` lines 31–48):
```python
def test_no_write_methods_on_airflow_bridge():
    """AirflowBridge must have zero POST/PUT/DELETE/PATCH methods."""
    from terminair.dbt.airflow_bridge import AirflowBridge

    members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
    write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
    assert not write_methods, f"Found write methods: {write_methods}"


def test_no_write_calls_in_source():
    """Source file must not contain any self._client.post/put/delete/patch calls."""
    import pathlib

    source = pathlib.Path("terminair/dbt/airflow_bridge.py").read_text()
    for verb in ("post", "put", "delete", "patch"):
        assert f"self._client.{verb}" not in source, (
            f"Found forbidden call 'self._client.{verb}' in airflow_bridge.py"
        )
```

**Replacement pattern for `test_read_only.py`:**
```python
"""Tests to enforce read-only contract for AirflowBridge."""

from __future__ import annotations

import inspect


def test_airflow_bridge_has_no_write_methods():
    """AirflowBridge must have zero POST/PUT/DELETE/PATCH methods."""
    from terminair.dbt.airflow_bridge import AirflowBridge

    members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
    write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
    assert not write_methods, f"Found write methods: {write_methods}"
```

**Import path note:** Correct import is `from terminair.dbt.airflow_bridge import AirflowBridge` — not `terminair.api.airflow_bridge` (that path does not exist).

---

### `Dockerfile` (config, request-response)

**Analog:** Self-modification. Current file (`Dockerfile` lines 1–17):
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AIRFLOW_URL=http://localhost:8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY terminair ./terminair
COPY docs ./docs

RUN pip install --no-cache-dir -e .

VOLUME ["/app/target"]

CMD ["python", "-m", "terminair", "--demo"]
```

**Required change — CMD line only:**

Replace the exec-form CMD with a shell-form CMD that conditionally uses `$AIRFLOW_URL` when `TERMINAIR_DEMO` is not set and `TERMINAIR_USER` is set; otherwise falls back to `--demo`:

```dockerfile
CMD if [ -n "$AIRFLOW_URL" ] && [ "$TERMINAIR_DEMO" != "1" ]; then \
      exec python -m terminair --url "$AIRFLOW_URL" ${TERMINAIR_USER:+--user "$TERMINAIR_USER"}; \
    else \
      exec python -m terminair --demo; \
    fi
```

**Password handling note:** `cli.py` line 60 already checks `TERMINAIR_PASSWORD` env var. The container non-demo path relies on `TERMINAIR_PASSWORD` being set to avoid an interactive prompt blocking non-TTY containers (pitfall documented in RESEARCH.md line 209-215).

**All other Dockerfile lines are correct** — `VOLUME ["/app/target"]` satisfies BLD-03's "mounts local target/ directory" requirement.

---

## Shared Patterns

### inspect-based write-method assertion
**Source:** `terminair/tests/dbt/test_airflow_bridge.py` lines 31–37
**Apply to:** `terminair/tests/test_read_only.py`
```python
import inspect

members = dict(inspect.getmembers(SomeClass, predicate=inspect.isfunction))
write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
assert not write_methods, f"Found write methods: {write_methods}"
```

### ModelState construction for RegressionAnalyzer tests
**Source:** `terminair/tests/dbt/test_regression_and_mock.py` lines 21–41
**Apply to:** `terminair/tests/dbt/test_regression.py` (upstream_schema_change test)

Required fields with no default (must always be provided):
```python
ModelState(
    node_id="model.p.<name>",
    name="<name>",
    tag="<tag>",
    status="success",
    dag_id="",
    task_id="",
    materialization="view|table|incremental",
    schema_name="s",
    database_name="d",
    has_upstream_failure=False,
    # optional: upstream_deps=["model.p.dep_id"]  # required for upstream_schema_change
)
```

### pytest class structure (no fixtures needed)
**Source:** `terminair/tests/dbt/test_regression_and_mock.py` — all test classes
**Apply to:** `test_regression.py`, `test_mock_data.py`

Pattern: classes with no `__init__`, imports inside each test method, no class-level fixtures. This is intentional — the project uses monkeypatch only, not mocking frameworks.

---

## No Analog Found

All files in scope have direct analogs or self-reference (Dockerfile).

---

## Metadata

**Analog search scope:** `terminair/tests/`, `terminair/tests/dbt/`, `terminair/dbt/`
**Files scanned:** 6 (test_regression_and_mock.py, test_airflow_bridge.py, test_read_only.py, regression.py, models.py, Dockerfile)
**Pattern extraction date:** 2026-05-15
