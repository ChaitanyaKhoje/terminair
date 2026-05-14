# Phase 2: dbt Data Layer - Research

**Researched:** 2026-05-14
**Domain:** dbt artifact parsing, Airflow REST API bridge, Python data layer architecture
**Confidence:** HIGH (schema facts verified against official sources; Airflow TaskInstance fields MEDIUM via web search cross-reference)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- StateAggregator is the single composition root — screens never call data sources directly
- MockDataProvider implements identical interface to StateAggregator (same return type: list[ModelState])
- SnowflakeClient must be injectable via dependency injection; TERMINAIR_MOCK_SNOWFLAKE=1 env var injects fixtures/query_history.json
- AirflowBridge is GET-only — zero POST/PUT/DELETE/PATCH methods (enforced by test_read_only.py later)
- All modules must be independently importable without side effects
- ManifestLoader grain extraction precedence: (1) unique_key config, (2) partition_by.field, (3) schema.yml unique+not_null combo, (4) fallback []
- var() regex: `var\(['"](\w+)['"](?:,\s*([^)]+))?\)` against raw_code or compiled_code
- RegressionAnalyzer thresholds: row_drop -10% to -30% = warning; <-30% = critical; row_spike >+50% = warning; grain_added = warning; grain_removed = critical; upstream_schema_change = warning; new_model_no_baseline = info
- MockDataProvider: 10 models, tag distribution finance(3), marketing(2), core(2), platform(2), risk(1)
- Unit tests go in terminair/tests/dbt/ (new subdirectory)

### Claude's Discretion

- Internal helpers and private methods are at Claude's discretion
- Error handling: raise specific exceptions (not bare except) for callers to handle
- Fixture JSON structure must match real dbt manifest v10+ schema conventions

### Deferred Ideas (OUT OF SCOPE)

- Real Snowflake connection (INFORMATION_SCHEMA.QUERY_HISTORY) — Phase 2 only needs the interface and mock
- Kubernetes pod name resolution — pod_name is nullable, always None in fixture data
- Automated manifest_previous.json capture — manual archive documented only
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DAT-01 | ManifestLoader: node lookup, tag index, deps, lineage, grain, ref/source/var, config | dbt manifest v10 schema verified — field names confirmed: `raw_code`, `compiled_code`, `depends_on.nodes`, `config.unique_key` |
| DAT-02 | ArtifactReader: run_results.json + run_results_previous.json, timing, row counts, errors | run_results v5 schema verified — `adapter_response.rows_affected`, `timing[].started_at/completed_at`, `unique_id` keying |
| DAT-03 | AirflowBridge: dag_names → task scan → fuzzy match → {node_id: (status, pod_name)} | Airflow v1 REST: `/api/v1/dags/{dag_id}/dagRuns/~/taskInstances`, `hostname` field confirmed |
| DAT-04 | SnowflakeClient: bytes_scanned per model, mockable via DI, TERMINAIR_MOCK_SNOWFLAKE=1 | DI pattern researched; env-var-controlled mock is idiomatic Python |
| DAT-05 | StateAggregator: merge all sources → list[ModelState], compute has_upstream_failure | Composition pattern clear from design spec; no external library needed |
| DAT-06 | RegressionAnalyzer: 6 signal types, severity thresholds, critical-first sort | Pure Python, thresholds locked in CONTEXT.md |
| DAT-07 | MockDataProvider: 10 models, all status types, all signals, tick() transitions | Pure Python dataclass construction |
| FIX-01 | fixtures/manifest.json — 10 models, v10 schema, unique_key, depends_on, compiled_code | v10 field names verified: raw_code, compiled_code, depends_on.nodes list |
| FIX-02 | fixtures/run_results.json — 2 running, 1 self-failed, 1 upstream-failed, 2 queued, 4 success | v5 schema confirmed: status, timing, adapter_response.rows_affected |
| FIX-03 | fixtures/run_results_previous.json — baseline with row_drop trigger models | Same schema as FIX-02; rows_affected values chosen to trigger -25%+ delta |
| FIX-04 | fixtures/manifest_previous.json — 1 model with different unique_key for grain_added | Same manifest v10 schema; unique_key differs for one node |
| FIX-05 | fixtures/query_history.json — Snowflake mock with bytes_scanned per model | Custom JSON format; no external schema constraint |
</phase_requirements>

---

## Summary

Phase 2 builds a pure-Python data layer — no UI, no Textual, no new external dependencies. All seven modules can be implemented using libraries already in `pyproject.toml` (httpx, pydantic, standard library). The primary technical challenge is getting the dbt artifact field names exactly right: dbt 1.6+ (manifest v10) renamed `raw_sql`→`raw_code` and `compiled_sql`→`compiled_code`, and the same rename happened in run_results v5 (`compiled_code` in results). Any fixture that uses the old names will silently fail because ManifestLoader will find `None` where it expects SQL strings.

The Airflow bridge is conceptually simple but has one important design choice: because there is no `pod_name` field in the Airflow v2 REST API (the field is `hostname`), the design doc's instruction to "get hostname/pod_name" means using `hostname` and treating it as the pod_name proxy. For Kubernetes executor setups, hostname and pod name may differ; the design doc acknowledges this as a v1 limitation.

For fuzzy matching (task_id → manifest node name), `difflib.get_close_matches` is the correct choice: it requires no new dependency, handles the small datasets involved (<100 task IDs per DAG), and provides configurable cutoff. rapidfuzz is faster but is not installed, would add a C extension dependency, and the performance gain is irrelevant at this scale.

**Primary recommendation:** Implement all modules strictly against the v10/v5 artifact schema field names (`raw_code`, `compiled_code`), use `difflib.get_close_matches` with cutoff=0.6, and use `httpx.AsyncClient` with persistent `BasicAuth` constructed from the existing `Connection` model.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Manifest parsing (node structure, lineage, grain) | Data Layer (`terminair/dbt/`) | — | Pure filesystem I/O + Python logic; no UI involvement |
| Run result parsing (status, timing, row counts) | Data Layer (`terminair/dbt/`) | — | Filesystem I/O; screens consume aggregated ModelState only |
| Airflow task status fetch | Data Layer (`terminair/dbt/`) | Airflow REST API | GET-only bridge; screens never call Airflow directly |
| Snowflake bytes_scanned | Data Layer (`terminair/dbt/`) | SnowflakeClient (injectable) | Optional enrichment; mockable at construction time |
| Model state composition | StateAggregator | — | Single composition root; all sources converge here |
| Regression signal detection | RegressionAnalyzer | — | Pure computation on list[ModelState]; stateless |
| Demo/offline mode | MockDataProvider | — | Drop-in for StateAggregator; no network or filesystem needed |
| Config (connection, paths) | `terminair/config.py` (existing) | Phase 3 extends | DbtConfig/SnowflakeConfig added in Phase 3; Phase 2 consumes raw paths |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | built-in | Load manifest.json, run_results.json | No dependency; dbt artifacts are plain JSON |
| Python stdlib `pathlib` | built-in | Path handling for artifact files | Established pattern in config.py |
| Python stdlib `dataclasses` | built-in | ModelState, RegressionSignal | Design doc specifies @dataclass, not Pydantic |
| Python stdlib `difflib` | built-in | Fuzzy match task_id → node name | No new dependency; sufficient at <100 items/DAG |
| Python stdlib `re` | built-in | var() extraction regex | Standard for regex extraction |
| `httpx` | 0.28.1 (installed) | AirflowBridge async HTTP | Already in pyproject.toml; existing pattern in codebase |
| `pydantic` v2 | 2.13.0 (installed) | Config models (Connection reuse) | Already in pyproject.toml; used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | installed | Test async AirflowBridge methods | asyncio_mode = "auto" already configured |
| `respx` | installed | Mock httpx calls in AirflowBridge tests | Already in dev dependencies |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `difflib.get_close_matches` | `rapidfuzz` | rapidfuzz is 40% faster but not installed; adds C extension dependency; performance irrelevant at <100 task IDs |
| `@dataclass` for ModelState | Pydantic BaseModel | Design doc explicitly specifies @dataclass; Pydantic adds validation overhead not needed for internal data |
| Manual JSON loading | dbt's own `dbt-core` package | dbt-core is a very heavy dependency; manifest.json is plain JSON with a stable schema |

**Installation:** No new packages needed. All required libraries are in existing `pyproject.toml`.

---

## Architecture Patterns

### System Architecture Diagram

```
Local filesystem                  Airflow REST API           Snowflake (optional)
  manifest.json    run_results.json    /api/v1/dags/{id}/       INFORMATION_SCHEMA
  (current+prev)   (current+prev)      dagRuns/~/taskInstances  (deferred to v2)
        │                 │                    │                       │
        ▼                 ▼                    ▼                       ▼
  ManifestLoader    ArtifactReader       AirflowBridge          SnowflakeClient
  - load()          - get_result()       - get_task_statuses()  - get_bytes_scanned()
  - get_node()      - get_previous()     (async, GET only)      (injectable mock)
  - get_grain()     (handles missing                            (TERMINAIR_MOCK_SNOWFLAKE)
  - get_lineage()    prev gracefully)
        │                 │                    │                       │
        └─────────────────┴────────────────────┴───────────────────────┘
                                    │
                            StateAggregator.get_models()
                            - merges all sources
                            - computes has_upstream_failure
                            - returns list[ModelState]
                                    │
                    ┌───────────────┤
                    │               │
            RegressionAnalyzer   Screens (Phase 4)
            .analyze()           consume list[ModelState]
            returns list[RegressionSignal]
                    │
            also consumed by screens

  MockDataProvider (drop-in when manifest.json missing)
  .get_models() → list[ModelState] (same interface, async def)
  .tick() → increments duration, transitions running→success after 4 ticks
```

### Recommended Project Structure
```
terminair/
  dbt/
    __init__.py          # exports ModelState, RegressionSignal dataclasses + public API
    manifest.py          # ManifestLoader
    artifacts.py         # ArtifactReader
    airflow_bridge.py    # AirflowBridge (async, GET only)
    snowflake_client.py  # SnowflakeClient (sync, injectable mock)
    aggregator.py        # StateAggregator
    regression.py        # RegressionAnalyzer
    mock_data.py         # MockDataProvider
    fixtures/
      manifest.json
      manifest_previous.json
      run_results.json
      run_results_previous.json
      query_history.json
  tests/
    dbt/
      __init__.py        # empty — required for pytest discovery
      test_manifest.py
      test_regression.py
      test_aggregator.py
      test_mock_data.py
```

### Pattern 1: dbt Manifest v10 Node Structure (CRITICAL — field name changes)

**What:** dbt 1.6 (manifest schema v10) renamed `raw_sql`→`raw_code` and `compiled_sql`→`compiled_code`. Code that reads the old names gets `None`.

**When to use:** Every read of node SQL content and config.

```python
# Source: schemas.getdbt.com/dbt/manifest/v10 [VERIFIED]
node = manifest["nodes"]["model.project.fct_revenue_daily"]

# CORRECT field names in v10+
raw_code = node.get("raw_code")           # NOT raw_sql
compiled_code = node.get("compiled_code") # NOT compiled_sql

# depends_on structure
upstream_nodes = node["depends_on"]["nodes"]    # list[str] of unique_ids
upstream_macros = node["depends_on"]["macros"]  # list[str]

# unique_key: Union[str, list[str], None]
unique_key = node.get("config", {}).get("unique_key")
if isinstance(unique_key, str):
    grain = [unique_key]
elif isinstance(unique_key, list):
    grain = unique_key
else:
    grain = []  # falls through to next precedence

# partition_by: dict with "field" key (BigQuery pattern; not always present)
partition_by = node.get("config", {}).get("partition_by")
if partition_by and isinstance(partition_by, dict):
    grain = [partition_by["field"]]

# node unique_id format: "<resource_type>.<package_name>.<resource_name>"
# example: "model.my_project.fct_revenue_daily"
```

### Pattern 2: run_results.json v5 Schema

**What:** Results are an array keyed by `unique_id`. Row counts live inside `adapter_response`.

```python
# Source: schemas.getdbt.com/dbt/run-results/v5/index.html [VERIFIED]
with open("run_results.json") as f:
    data = json.load(f)

for result in data["results"]:
    node_id = result["unique_id"]          # maps to manifest nodes key
    status = result["status"]              # "success" | "error" | "skipped"
    execution_time = result["execution_time"]  # float seconds

    # Row count lives in adapter_response — adapter-dependent
    rows_affected = (
        result.get("adapter_response", {}).get("rows_affected")
    )  # int or None; None if DDL/view materialization

    # Timing breakdown (compile + execute steps)
    timing = result.get("timing", [])
    execute_step = next((t for t in timing if t["name"] == "execute"), None)
    started_at = execute_step["started_at"] if execute_step else None
    completed_at = execute_step["completed_at"] if execute_step else None

    # Error details (for failed models)
    message = result.get("message")        # human-readable error string
```

**Important note on row counts:** `rows_affected` is adapter-specific. For Snowflake `table`/`incremental` materializations it reflects rows written. For `view` materializations it is typically `None` or 0. The fixture should reflect this — view nodes should have `None` for row counts.

### Pattern 3: AirflowBridge with httpx AsyncClient

**What:** Persistent-auth async client using existing Connection config.

```python
# Source: python-httpx.org/advanced/authentication/ [VERIFIED]
import httpx
from terminair.config import Connection

class AirflowBridge:
    def __init__(self, connection: Connection) -> None:
        auth = httpx.BasicAuth(
            username=connection.auth.username,
            password=connection.auth.password,
        )
        self._client = httpx.AsyncClient(
            base_url=connection.url,
            auth=auth,
            timeout=10.0,
        )

    async def get_task_statuses(
        self, dag_names: list[str], node_names: list[str]
    ) -> dict[str, tuple[str, str | None]]:
        """Returns {node_id: (airflow_state, hostname_or_None)}."""
        result: dict[str, tuple[str, str | None]] = {}
        for dag_id in dag_names:
            # Get most recent DAG run
            runs_resp = await self._client.get(
                f"/api/v1/dags/{dag_id}/dagRuns",
                params={"limit": 1, "order_by": "-execution_date"},
            )
            runs_resp.raise_for_status()
            runs = runs_resp.json().get("dag_runs", [])
            if not runs:
                continue
            dag_run_id = runs[0]["dag_run_id"]

            # Get all task instances for that run
            ti_resp = await self._client.get(
                f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
            )
            ti_resp.raise_for_status()
            for ti in ti_resp.json().get("task_instances", []):
                task_id = ti["task_id"]
                matched = _fuzzy_match(task_id, node_names)
                if matched:
                    result[matched] = (ti["state"], ti.get("hostname"))
        return result

    async def close(self) -> None:
        await self._client.aclose()
```

### Pattern 4: Fuzzy Match with difflib

**What:** Match Airflow task_id strings to manifest node names.

```python
# Source: Python stdlib docs [VERIFIED — built-in module]
import difflib

def _fuzzy_match(task_id: str, node_names: list[str]) -> str | None:
    """Match a task_id to a manifest node name. Returns node_id or None."""
    # Try substring first (exact case-insensitive match)
    for name in node_names:
        if name.lower() in task_id.lower() or task_id.lower() in name.lower():
            return f"model.my_project.{name}"  # caller builds full node_id

    # Fall back to difflib close match
    matches = difflib.get_close_matches(
        task_id, node_names, n=1, cutoff=0.6
    )
    return matches[0] if matches else None
```

**Note:** The cutoff of 0.6 is a starting point. The actual matching maps task_id strings (e.g., `run_fct_revenue_daily`) to node names (e.g., `fct_revenue_daily`). Substring matching handles the common prefix/suffix patterns (`run_`, `dbt_`) before falling back to difflib.

### Pattern 5: Dependency Injection for SnowflakeClient

**What:** Constructor-time injection; env var selects implementation.

```python
# [ASSUMED] — standard Python DI pattern, no external library needed
import os
import json
from pathlib import Path

class SnowflakeClient:
    def __init__(self, fixture_path: Path | None = None) -> None:
        self._mock = os.environ.get("TERMINAIR_MOCK_SNOWFLAKE", "").strip() in ("1", "true")
        self._fixture_path = fixture_path or (
            Path(__file__).parent / "fixtures" / "query_history.json"
        )
        self._mock_data: dict[str, int] | None = None
        if self._mock:
            with open(self._fixture_path) as f:
                self._mock_data = json.load(f)

    def get_bytes_scanned(self, model_name: str) -> int | None:
        if self._mock and self._mock_data:
            return self._mock_data.get(model_name)
        # Real Snowflake implementation deferred to v2
        return None
```

### Pattern 6: ModelState and RegressionSignal as Dataclasses

```python
# Source: design doc (2026-05-14-dbt-intelligence-design.md) [CITED]
from dataclasses import dataclass, field

@dataclass
class ModelState:
    node_id: str
    name: str
    tag: str                    # primary tag (first in all_tags)
    all_tags: list[str]
    status: str                 # running | success | failed | queued | skipped
    duration_s: float | None
    rows_written: int | None
    rows_previous: int | None
    row_delta_pct: float | None # (rows_written - rows_previous) / rows_previous * 100
    bytes_scanned: int | None
    dag_id: str
    task_id: str
    pod_name: str | None
    warehouse: str | None
    error_message: str | None
    upstream_deps: list[str]
    downstream_deps: list[str]
    upstream_statuses: dict[str, str]
    has_upstream_failure: bool   # computed by StateAggregator
    materialization: str
    grain_columns: list[str]
    refs: list[str]
    sources: list[str]
    dbt_vars: dict[str, str]
    config_block: dict
    compiled_sql: str | None     # design doc uses compiled_sql as the field name in ModelState
    schema_name: str
    database_name: str
    run_started_at: str | None
    run_finished_at: str | None
```

**Note on field naming:** The `ModelState.compiled_sql` field uses "compiled_sql" as the Python attribute name (it's an internal data class field, not a JSON key). The manifest v10 artifact uses `compiled_code` as the JSON key. ManifestLoader reads `compiled_code` from the artifact and stores it in `ModelState.compiled_sql`. This is intentional separation between the artifact schema and the internal data model.

### Anti-Patterns to Avoid

- **Reading `raw_sql` or `compiled_sql` from manifest JSON:** These field names were retired in dbt 1.5 (manifest v9). v10 uses `raw_code` and `compiled_code`. Fixtures must also use v10 names.
- **Calling data sources from screens:** Screens must consume only `list[ModelState]` from StateAggregator or MockDataProvider.
- **Bare `except Exception: pass` in loaders:** Established project rule — always `except Exception as e: raise SpecificError(str(e))`.
- **Side effects on import:** Each module must be importable standalone. No module-level HTTP calls, file reads, or env var parsing that can raise.
- **Hardcoding `rows_affected` as the row count field name for all adapters:** Some adapters use different keys. Use `.get("rows_affected")` defensively; treat missing as None.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom edit-distance | `difflib.get_close_matches` | Built-in, configurable cutoff, sufficient at <100 items |
| Async HTTP with auth | Custom auth header injection | `httpx.BasicAuth` + `AsyncClient` | Already used; handles redirects, retries, cleanup |
| JSON schema validation for manifest | Custom schema checker | Trust the schema version field + defensive `.get()` | dbt artifacts are stable; over-validation adds complexity |
| Graph traversal for lineage | Custom BFS | Python recursive dict traversal with depth limit | Simple tree; no cycles in dbt DAG |
| Row delta percentage | Custom statistics | `(current - previous) / previous * 100` | Trivial formula; no library needed |

**Key insight:** The entire data layer is pure Python with stdlib + httpx. Adding dependencies like `networkx` (graph), `pandas` (tabular), or `dbt-core` (artifact parsing) would introduce heavyweight transitive deps for problems that are trivially solvable with stdlib.

---

## Common Pitfalls

### Pitfall 1: Wrong manifest field names (raw_sql vs raw_code)
**What goes wrong:** ManifestLoader returns `None` for all SQL content; var() regex finds nothing; grain extraction falls back silently to [].
**Why it happens:** dbt renamed these fields in v1.5 (manifest v9) and v1.6 (manifest v10). Training data and docs still mention both names.
**How to avoid:** Always use `raw_code` and `compiled_code` in both code and fixture files. Cross-check: if any node in fixture has `raw_sql`, it's wrong.
**Warning signs:** All `dbt_vars` dicts are empty even for models with known var() calls; `compiled_sql` field in ModelState is always None.

### Pitfall 2: Treating run_results as keyed by node_id (it's a list)
**What goes wrong:** O(n²) lookup or KeyError when trying `results[node_id]`.
**Why it happens:** The file's `results` key is a JSON array, not a dict. Each element has a `unique_id` field.
**How to avoid:** Build an index dict on load: `{r["unique_id"]: r for r in data["results"]}`.
**Warning signs:** `TypeError: list indices must be integers or slices, not str`.

### Pitfall 3: Missing __init__.py in tests/dbt/
**What goes wrong:** pytest can't discover tests in the new subdirectory.
**Why it happens:** pyproject.toml has `testpaths = ["terminair/tests"]` — pytest traverses subdirs but needs `__init__.py` for package-style imports.
**How to avoid:** Create `terminair/tests/dbt/__init__.py` (empty) in Wave 0 before any test file.
**Warning signs:** `collected 0 items` when running pytest against the dbt test subdir.

### Pitfall 4: AirflowBridge AsyncClient lifecycle in tests
**What goes wrong:** `ResourceWarning: Unclosed client session` during tests.
**Why it happens:** AsyncClient must be explicitly closed (or used as async context manager).
**How to avoid:** Implement `async def close(self)` and call it in test teardown. Alternatively, use `async with httpx.AsyncClient() as client:` inside methods — but this loses the persistent-auth efficiency benefit. For this codebase size, `close()` method on the class is sufficient.
**Warning signs:** ResourceWarning in test output even when tests pass.

### Pitfall 5: has_upstream_failure computed incorrectly
**What goes wrong:** Models show `has_upstream_failure=False` when they have a skipped upstream (not just failed).
**Why it happens:** The design doc defines: "true if any upstream is `failed` or `skipped`". Both statuses must be checked.
**How to avoid:** `has_upstream_failure = any(v in ("failed", "skipped") for v in upstream_statuses.values())`.
**Warning signs:** Upstream-caused failures show `has_upstream_failure=False`; upstream-caused vs self-caused distinction broken in ProblemsScreen (Phase 4).

### Pitfall 6: Airflow API — no pod_name field; use hostname
**What goes wrong:** Code tries to read `ti["pod_name"]` and gets KeyError.
**Why it happens:** The Airflow REST API task instance response has `hostname` not `pod_name`. For Kubernetes executor, the hostname is set to the pod name, but the JSON key is `hostname`.
**How to avoid:** Read `ti.get("hostname")` — use this as pod_name proxy. Store in `ModelState.pod_name`. This is always `None` in local Airflow (not Kubernetes).
**Warning signs:** KeyError on `ti["pod_name"]` when processing real API responses.

### Pitfall 7: Circular import between terminair.dbt and terminair.config
**What goes wrong:** `ImportError: cannot import name 'Connection' from partially initialized module`.
**Why it happens:** If `terminair/dbt/__init__.py` imports from `terminair.config` at module level, and `terminair.config` is extended (Phase 3) to import from `terminair.dbt`, a circular import forms.
**How to avoid:** Phase 2 is safe — config.py does not import from dbt/. Maintain this direction (dbt imports config, config never imports dbt). If type hints are needed across the boundary, use `TYPE_CHECKING` guards.
**Warning signs:** `ImportError` or `AttributeError: partially initialized module`.

---

## Code Examples

### Fixture manifest.json node structure (v10-compliant)
```json
{
  "metadata": {
    "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v10/manifest.json",
    "dbt_version": "1.6.5",
    "generated_at": "2026-05-14T10:00:00Z",
    "invocation_id": "abc123",
    "env": {}
  },
  "nodes": {
    "model.my_project.fct_revenue_daily": {
      "unique_id": "model.my_project.fct_revenue_daily",
      "name": "fct_revenue_daily",
      "resource_type": "model",
      "package_name": "my_project",
      "path": "finance/fct_revenue_daily.sql",
      "original_file_path": "models/finance/fct_revenue_daily.sql",
      "fqn": ["my_project", "finance", "fct_revenue_daily"],
      "alias": "fct_revenue_daily",
      "schema": "analytics",
      "database": "prod",
      "description": "Daily revenue fact table",
      "tags": ["finance", "core"],
      "config": {
        "materialized": "incremental",
        "unique_key": "revenue_date",
        "incremental_strategy": "merge",
        "on_schema_change": "sync_all_columns",
        "tags": ["finance", "core"],
        "enabled": true,
        "alias": null,
        "schema": null,
        "database": null,
        "full_refresh": null
      },
      "depends_on": {
        "macros": [],
        "nodes": [
          "model.my_project.stg_payments",
          "model.my_project.stg_orders"
        ]
      },
      "raw_code": "SELECT\n  {{ var('revenue_date', 'current_date') }} as revenue_date,\n  sum(amount) as total_revenue\nFROM {{ ref('stg_payments') }}\nJOIN {{ ref('stg_orders') }} using (order_id)",
      "compiled_code": "SELECT\n  current_date as revenue_date,\n  sum(amount) as total_revenue\nFROM analytics.stg_payments\nJOIN analytics.stg_orders using (order_id)",
      "columns": {},
      "meta": {},
      "refs": [["stg_payments"], ["stg_orders"]],
      "sources": []
    }
  },
  "sources": {},
  "exposures": {},
  "metrics": {},
  "selectors": {},
  "parent_map": {
    "model.my_project.fct_revenue_daily": [
      "model.my_project.stg_payments",
      "model.my_project.stg_orders"
    ]
  },
  "child_map": {
    "model.my_project.fct_revenue_daily": [
      "model.my_project.mart_revenue"
    ]
  }
}
```

**Source:** schemas.getdbt.com/dbt/manifest/v10 [VERIFIED] — field names `raw_code`, `compiled_code`, `depends_on.nodes` as list[str], `config.unique_key` as str or list.

### Fixture run_results.json node structure (v5-compliant)
```json
{
  "metadata": {
    "dbt_schema_version": "https://schemas.getdbt.com/dbt/run-results/v5/run-results.json",
    "dbt_version": "1.6.5",
    "generated_at": "2026-05-14T10:05:00Z",
    "invocation_id": "abc123",
    "env": {}
  },
  "elapsed_time": 142.5,
  "results": [
    {
      "unique_id": "model.my_project.fct_revenue_daily",
      "status": "success",
      "execution_time": 12.4,
      "thread_id": "Thread-1",
      "compiled": true,
      "compiled_code": "SELECT current_date ...",
      "relation_name": "prod.analytics.fct_revenue_daily",
      "message": "CREATE TABLE",
      "failures": null,
      "adapter_response": {
        "rows_affected": 22000,
        "code": "SUCCESS",
        "_message": "SUCCESS 22000"
      },
      "timing": [
        {
          "name": "compile",
          "started_at": "2026-05-14T10:00:01.000Z",
          "completed_at": "2026-05-14T10:00:01.500Z"
        },
        {
          "name": "execute",
          "started_at": "2026-05-14T10:00:01.500Z",
          "completed_at": "2026-05-14T10:00:13.900Z"
        }
      ]
    }
  ]
}
```

**Source:** schemas.getdbt.com/dbt/run-results/v5/index.html [VERIFIED]

### var() extraction pattern
```python
# Source: CONTEXT.md decision [CITED]
import re
_VAR_PATTERN = re.compile(r"""var\(['"](\w+)['"](?:,\s*([^)]+))?\)""")

def get_dbt_vars(raw_code: str | None, compiled_code: str | None) -> dict[str, str]:
    sql = raw_code or compiled_code or ""
    result = {}
    for match in _VAR_PATTERN.finditer(sql):
        var_name = match.group(1)
        default = match.group(2)
        result[var_name] = (default.strip().strip("'\"") if default else "REQUIRED")
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `raw_sql` / `compiled_sql` in manifest | `raw_code` / `compiled_code` | dbt 1.5 (manifest v9) | Fixtures and parsers must use new names |
| `compiled_sql` in run_results | `compiled_code` in run_results | dbt 1.5 (run-results v4→v5) | Same rename applies in result objects |
| Airflow REST API v1 (`/api/v1/`) | Airflow REST API v2 (`/api/v2/`) in Airflow 3.x | Airflow 3.0 (2024) | Local demo stack uses Airflow 2.x; use v1 endpoint paths |

**Deprecated/outdated:**
- `raw_sql` / `compiled_sql`: retired in manifest v9. Any fixture, code, or documentation referencing these names is outdated.
- Airflow v1 REST API: still valid for Airflow 2.x (what the local demo stack runs); if Airflow 3.x is used, endpoints become `/api/v2/` with some schema changes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Airflow task instance response has `hostname` field (not `pod_name`) | Pitfall 6, Pattern 3 | AirflowBridge reads wrong field; pod_name always None even when set — low risk since pod_name is nullable and rendered as `--` |
| A2 | Airflow v1 endpoint `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances` returns `task_instances` array with `state` (not `status`) and `hostname` fields | Pattern 3 | AirflowBridge gets 200 but parses empty/wrong data — recoverable by adding a log statement |
| A3 | `rows_affected` in `adapter_response` is the correct key for Snowflake row counts in run_results.json | Pitfall 1, FIX-02 | Row count always None in fixtures → row_delta_pct always None → no row_drop/row_spike signals in mock |
| A4 | The local demo Airflow stack runs Airflow 2.x (v1 REST API endpoints) | Pattern 3 | If 3.x: endpoint paths would be `/api/v2/`, breaking AirflowBridge GET calls |
| A5 | `child_map` and `parent_map` in manifest.json provide downstream and upstream deps respectively | Pattern 1, DAT-01 | ManifestLoader would need to compute these from `depends_on.nodes` instead — trivially fixable |

---

## Open Questions (RESOLVED)

1. **Airflow REST API: exact task_instances response field for state**
   - What we know: Airflow's OpenAPI spec calls it `state` (not `status`); task instance model docs list `state` as the field
   - What's unclear: Whether `state` can be `running` (Airflow typically uses `running`) or maps differently to dbt's status vocabulary
   - RESOLVED: Use `ti.get("state", "unknown")` and implement a status mapping: `{"running": "running", "success": "success", "failed": "failed", "queued": "queued", "skipped": "skipped", "upstream_failed": "failed"}`. This mapping is implemented as `_STATE_MAP` in airflow_bridge.py.

2. **Does parent_map / child_map always exist in dbt manifest v10?**
   - What we know: The manifest documentation mentions `parent_map` and `child_map` as top-level keys
   - What's unclear: Whether they are always populated or only after `dbt docs generate`
   - RESOLVED: ManifestLoader falls back to building deps from `nodes[id]["depends_on"]["nodes"]` if parent_map is empty or absent. Both code paths are implemented and tested.

3. **pytest test discovery for terminair/tests/dbt/ subdirectory**
   - What we know: pyproject.toml has `testpaths = ["terminair/tests"]`; pytest 8.x discovers subdirs automatically
   - What's unclear: Whether `__init__.py` is needed in `tests/dbt/` for the current pytest-asyncio setup
   - RESOLVED: Create empty `__init__.py` in `tests/dbt/` — safe either way, prevents discovery issues. This is implemented as the first file created in 02-05-PLAN.md Task 1.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all modules | ✓ | 3.11.15 (via uv) | — |
| httpx | AirflowBridge | ✓ | 0.28.1 | — |
| pydantic | config integration | ✓ | 2.13.0 | — |
| pytest | all tests | ✓ | 9.0.3 (via uv) | — |
| pytest-asyncio | async bridge tests | ✓ | 1.3.0 | — |
| respx | mock httpx in tests | ✓ | 0.23.1 | — |
| difflib | fuzzy matching | ✓ | stdlib | — |
| rapidfuzz | NOT used | ✗ | not installed | difflib (chosen) |
| Airflow (local) | AirflowBridge integration | not checked | unknown | AirflowBridge returns {} gracefully when unreachable |
| Snowflake | SnowflakeClient | not checked | — | TERMINAIR_MOCK_SNOWFLAKE=1 |

**Missing dependencies with no fallback:** None — all required libraries are available.

**Missing dependencies with fallback:** Airflow and Snowflake services are optional; both have in-code fallback paths.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest terminair/tests/dbt/ -x -q` |
| Full suite command | `uv run pytest terminair/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DAT-01 | ManifestLoader.get_grain_columns() precedence: unique_key > partition_by > tests > [] | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_grain_extraction_precedence -x` | ❌ Wave 0 |
| DAT-01 | ManifestLoader.get_dbt_vars() regex extraction | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_var_extraction -x` | ❌ Wave 0 |
| DAT-01 | ManifestLoader.get_full_lineage() traversal with depth limit | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_lineage_depth -x` | ❌ Wave 0 |
| DAT-01 | ManifestLoader.build_tag_index() groups nodes by tag | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_tag_index -x` | ❌ Wave 0 |
| DAT-02 | ArtifactReader missing previous file → rows_previous=None | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_missing_previous_graceful -x` | ❌ Wave 0 |
| DAT-03 | AirflowBridge has no POST/PUT/DELETE/PATCH methods | unit | `uv run pytest terminair/tests/test_read_only.py -x` | ✅ (placeholder) |
| DAT-06 | RegressionAnalyzer row_drop at -25% → critical | unit | `uv run pytest terminair/tests/dbt/test_regression.py::test_row_drop_critical -x` | ❌ Wave 0 |
| DAT-06 | RegressionAnalyzer results sorted critical-first | unit | `uv run pytest terminair/tests/dbt/test_regression.py::test_sort_order -x` | ❌ Wave 0 |
| DAT-07 | MockDataProvider.tick() transitions running→success after 4 ticks | unit | `uv run pytest terminair/tests/dbt/test_mock_data.py::test_tick_transitions -x` | ❌ Wave 0 |
| DAT-07 | MockDataProvider covers all 6 signal types | unit | `uv run pytest terminair/tests/dbt/test_mock_data.py::test_signal_coverage -x` | ❌ Wave 0 |
| FIX-01..05 | Fixtures load without error and match expected node count | unit | `uv run pytest terminair/tests/dbt/test_manifest.py::test_fixture_loads -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest terminair/tests/dbt/ -x -q`
- **Per wave merge:** `uv run pytest terminair/tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `terminair/tests/dbt/__init__.py` — empty, required for pytest discovery
- [ ] `terminair/tests/dbt/test_manifest.py` — covers DAT-01, DAT-02, FIX-01..05
- [ ] `terminair/tests/dbt/test_regression.py` — covers DAT-06
- [ ] `terminair/tests/dbt/test_aggregator.py` — covers DAT-05
- [ ] `terminair/tests/dbt/test_mock_data.py` — covers DAT-07
- [ ] `terminair/dbt/fixtures/` directory with 5 fixture files

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | httpx.BasicAuth (credentials from config, not hardcoded) |
| V3 Session Management | no | No sessions; each httpx call is stateless |
| V4 Access Control | no | Read-only GET bridge; no authorization decisions |
| V5 Input Validation | yes | Pydantic for config; defensive `.get()` on all JSON fields |
| V6 Cryptography | no | No encryption in data layer |

### Known Threat Patterns for dbt/Airflow data layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential in fixture files | Information Disclosure | Fixtures use dummy values (`admin`/`admin`); no real credentials in `terminair/dbt/fixtures/` |
| Path traversal via manifest_path config | Tampering | `pathlib.Path` handles normalization; don't `eval()` path strings |
| SQL injection via compiled_code display | Tampering | Terminair is read-only; compiled_code is displayed as text, never executed |
| Airflow credentials in log output | Information Disclosure | Use `sanitize_error()` from `logging_utils.py` when logging httpx errors |

---

## Sources

### Primary (HIGH confidence)
- `schemas.getdbt.com/dbt/manifest/v10/index.html` — verified field names: `raw_code`, `compiled_code`, `depends_on.nodes`, `config.unique_key` type (str | list | None), `config.materialized`. Also confirmed dbt 1.6.5 as the corresponding version.
- `schemas.getdbt.com/dbt/run-results/v5/index.html` — verified: results array structure, `unique_id` keying, `status` enum values, `timing[].started_at/completed_at`, `adapter_response.rows_affected`, `execution_time`.
- `python-httpx.org/advanced/authentication/` — verified: `httpx.BasicAuth`, persistent client auth via constructor, per-request auth alternative.
- `docs.getdbt.com/reference/artifacts/run-results-json` — confirmed v6 schema (superset of v5); `adapter_response` dict structure, `rows_affected` key name.

### Secondary (MEDIUM confidence)
- Airflow REST API web search cross-reference — task instance fields include `hostname`, `state`, `task_id`, `dag_id`, `start_date`, `end_date`; endpoint path `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances` confirmed by multiple sources.
- `dev.to/mrquite/smart-text-matching-rapidfuzz-vs-difflib-ge5` — confirmed difflib sufficient for small datasets; rapidfuzz adds C extension for marginal gain at <100 items.

### Tertiary (LOW confidence)
- Airflow `parent_map` / `child_map` always present in manifest v10 — not explicitly verified; inferred from official manifest docs structure description.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already installed; versions verified with `python3 -c "import X; print(X.__version__)"`
- dbt artifact schema: HIGH — verified against official schemas.getdbt.com for both manifest v10 and run-results v5
- Architecture: HIGH — design doc is the canonical source; patterns are straightforward Python
- Airflow TaskInstance fields: MEDIUM — `hostname` and `state` confirmed by multiple secondary sources; exact JSON key names not verified against live Swagger spec
- Pitfalls: HIGH — manifest field rename (raw_sql→raw_code) is a concrete, documented breaking change with clear evidence

**Research date:** 2026-05-14
**Valid until:** 2026-11-14 (stable schema; dbt manifest v10 is not expected to change; Airflow v1 API is stable for 2.x)
