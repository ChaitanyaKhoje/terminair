# Terminair — dbt Model Intelligence TUI
**Design spec · 2026-05-14**

---

## Product definition

Terminair is a read-only local developer TUI for answering operational and structural questions about dbt models. It is NOT an Airflow TUI. Airflow is a data source for run status and pod context only. The `manifest.json` is the primary source of truth.

The developer runs terminair locally with:
- their dbt repo cloned (provides `target/manifest.json`, `target/run_results.json`)
- their Airflow app repo cloned (provides DAG definitions)
- a local Airflow demo stack running (provides live task status + pod names)

Snowflake is optional enrichment (bytes scanned only). All screens fall back gracefully when any source is unavailable.

---

## Core questions terminair answers

1. What is happening with this model right now?
2. Why is this model a problem?
3. Why is there a regression in this model or a model with added granularity?
4. What is the full hierarchy (lineage) for this model or tag?
5. What are the variables, refs, sources, and config for this model?

Every screen, panel, and keybind maps to one of these questions.

---

## What gets removed

The following screens are deleted entirely (files, imports, bindings):

- `screens/pools.py`
- `screens/health.py`
- `screens/sla_misses.py`
- `screens/resource_timeline.py`
- `screens/xcom_viewer.py`
- `screens/dags.py` (DAG list as primary view)
- `screens/dag_detail.py`
- `screens/dag_deps.py`
- `screens/dag_graph.py`
- `screens/task_instances.py`
- `screens/task_history.py`
- `screens/broken_summary.py`
- `screens/recent_activity.py`
- `screens/event_log.py`
- `screens/import_errors.py`
- `screens/watchlist.py`

The following tests are deleted (test Airflow-specific screens being removed):

- `tests/test_metrics.py`
- `tests/test_failure_heatmap.py`
- `tests/test_event_log_loader.py`

The following source modules are deleted:

- `api/client.py` (AirflowClient — replaced by AirflowBridge)
- `api/poller.py`
- `metrics/aggregations.py`
- `metrics/critical_path.py`
- `metrics/error_extract.py`
- `metrics/sparkline.py`
- `export.py`

---

## Architecture

```
dbt repo (local)          Airflow (local demo stack)      Snowflake (optional)
  target/manifest.json      REST API: DAG task list           bytes_scanned only
  target/run_results.json   REST API: task instance status
  target/run_results_prev   REST API: hostname (pod name)
         │                         │                                │
         ▼                         ▼                                ▼
   ManifestLoader          AirflowBridge                  SnowflakeClient
   ArtifactReader          (GET only, narrow)             (injectable mock)
         │                         │
         └──────────┬──────────────┘
                    ▼
            StateAggregator
            (merges into list[ModelState])
                    │
            RegressionAnalyzer
            (compares current vs prev run)
                    │
            ┌───────┴────────┐
            │                │
        Screens          MockDataProvider
     (all 4, wired       (injected when no
      to aggregator)      manifest found)
```

**Fallback chain:**
- manifest.json missing → MockDataProvider
- Airflow unreachable → status from run_results.json only, warning in topbar
- Snowflake block missing or connection fails → `bytes_scanned = None` silently
- `TERMINAIR_MOCK_SNOWFLAKE=1` → injects `fixtures/query_history.json`

**Screens are data-source agnostic.** They consume `list[ModelState]` from either `StateAggregator` or `MockDataProvider`. No screen calls Airflow, Snowflake, or the filesystem directly.

---

## File layout

```
terminair/
  dbt/
    __init__.py
    manifest.py          # ManifestLoader
    artifacts.py         # ArtifactReader (run_results.json)
    airflow_bridge.py    # AirflowBridge: status + pod_name only
    snowflake_client.py  # SnowflakeClient: bytes_scanned only
    aggregator.py        # StateAggregator -> list[ModelState]
    regression.py        # RegressionAnalyzer
    mock_data.py         # MockDataProvider
    fixtures/
      manifest.json
      manifest_previous.json
      run_results.json
      run_results_previous.json
      query_history.json

  screens/
    model_list.py        # ModelListScreen  (key 1)
    problems.py          # ProblemsScreen   (key 2)
    lineage.py           # LineageScreen    (key 3)
    model_detail.py      # ModelDetailScreen (Enter from any screen)

  tests/
    dbt/
      test_manifest.py
      test_regression.py
      test_aggregator.py
      test_mock_data.py
    test_read_only.py    # extended to cover AirflowBridge
    test_config.py       # unchanged
    test_flash.py        # unchanged
    test_command_palette.py  # unchanged
```

---

## Data model

```python
@dataclass
class ModelState:
    node_id: str               # model.project.fct_revenue_daily
    name: str
    tag: str                   # primary tag
    all_tags: list[str]
    status: str                # running | success | failed | queued | skipped
    duration_s: float | None
    rows_written: int | None
    rows_previous: int | None
    row_delta_pct: float | None  # (rows_written - rows_previous) / rows_previous * 100
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
    compiled_sql: str | None
    schema_name: str
    database_name: str
    run_started_at: str | None
    run_finished_at: str | None

@dataclass
class RegressionSignal:
    node_id: str
    name: str
    signal_type: str   # row_drop | row_spike | grain_added | grain_removed
                       # | upstream_schema_change | new_model_no_baseline
    severity: str      # warning | critical | info
    description: str
    row_delta_pct: float | None
    grain_before: list[str]
    grain_after: list[str]
    detail: str
```

---

## dbt layer modules

### manifest.py — ManifestLoader

```python
class ManifestLoader:
    def load(self) -> dict
    def get_node(self, node_id: str) -> dict | None
    def get_nodes_by_tag(self, tag: str) -> list[dict]
    def get_all_tags(self) -> list[str]
    def get_upstream_deps(self, node_id: str) -> list[str]
    def get_downstream_deps(self, node_id: str) -> list[str]
    def get_full_lineage(self, node_id: str, depth: int = -1) -> dict
    def get_grain_columns(self, node_id: str) -> list[str]
    def get_refs(self, node_id: str) -> list[str]
    def get_sources(self, node_id: str) -> list[str]
    def get_dbt_vars(self, node_id: str) -> dict[str, str]
    def get_config(self, node_id: str) -> dict
    def get_all_node_ids(self) -> list[str]
    def build_tag_index(self) -> dict[str, list[str]]
```

**Grain extraction precedence:**
1. `node.config.unique_key` (list or string)
2. `node.config.partition_by.field`
3. schema.yml tests where test name is `unique` and also has `not_null`
4. Fallback: `grain_columns = []`, signal includes "grain unknown"

**var() extraction:** regex `var\(['"](\w+)['"](?:,\s*([^)]+))?\)` against `raw_sql` or `compiled_sql`. Returns `{var_name: default_value_or_"REQUIRED"}`.

### artifacts.py — ArtifactReader

Reads `run_results.json` and `run_results_previous.json`. Returns per-node timing, row counts, status, error messages. If `run_results_previous.json` not found, `rows_previous = None` for all nodes.

### airflow_bridge.py — AirflowBridge

GET only. Receives `dag_names: list[str]` from config. For each DAG, fetches all tasks via Airflow REST API. Fuzzy-matches task IDs to manifest node names. Returns `{node_id: (status, pod_name)}`. `pod_name` comes from task instance `hostname` — nullable, renders as `--` if absent.

### aggregator.py — StateAggregator

Composes `ManifestLoader`, `ArtifactReader`, `AirflowBridge`, `SnowflakeClient` into `list[ModelState]`. Computes `has_upstream_failure` by walking `upstream_statuses` — true if any upstream is `failed` or `skipped`. This is the single composition root; screens never call data sources directly.

### regression.py — RegressionAnalyzer

```python
class RegressionAnalyzer:
    def __init__(self, current: list[ModelState], manifest: ManifestLoader)
    def analyze(self) -> list[RegressionSignal]  # sorted: critical first
    def signals_for_model(self, node_id: str) -> list[RegressionSignal]
```

**Signal thresholds:**

| Signal | Condition | Severity |
|---|---|---|
| `row_drop` | delta < -10% and > -30% | warning |
| `row_drop` | delta < -30% | critical |
| `row_spike` | delta > +50% | warning |
| `grain_added` | grain_columns current > previous | warning |
| `grain_removed` | grain_columns current < previous | critical |
| `upstream_schema_change` | upstream materialization or grain changed | warning |
| `new_model_no_baseline` | rows_previous is None AND status == success | info |

### mock_data.py — MockDataProvider

Implements the same interface as `StateAggregator`. Provides 10 models covering all screen paths:
- 2 running (duration increments each tick)
- 1 failed (own error_message — Snowflake SQL compilation error)
- 1 failed (has_upstream_failure=True, no own error)
- 2 queued
- 4 success
- 2 with row_delta_pct < -25% → `row_drop` signals
- 1 with grain_columns differing from previous → `grain_added` signal
- 1 with rows_previous = None → `new_model_no_baseline` signal
- Tags: finance(3), marketing(2), core(2), platform(2), risk(1)

`tick()` increments running model durations. After 4 ticks, transitions one running model to success and recomputes `row_delta_pct`.

---

## Screens

### ModelListScreen (key `1`)

Answers: "what is happening across all models right now"

```
┌─ terminair | dbt-watch | local | 14:32:01 | LIVE ──────────────────┐
│ [all] [finance] [marketing] [core] [risk]                           │
│ /filter...                                                          │
├─ Models ────────────────────────────────────────────────────────────┤
│ ● fct_revenue_daily    finance   running   0:42    22K    --        │
│ ✗ fct_orders           finance   failed    1:12    --     --        │
│ ○ stg_payments         core      queued    --      --     --        │
│ ✓ mart_platform_usage  platform  success   2:01   890K  +380%  ⚠   │
├─────────────────────────────────────────────────────────────────────┤
│ total:10  running:2  failed:2  queued:2  ⚠ 3 warnings              │
└─────────────────────────────────────────────────────────────────────┘
```

Columns: `[status]` | `model` | `tag` | `status_text` | `duration` | `rows` | `row_delta` | `dag_id`

`row_delta` column: colored +/- percentage, `--` if no prior run, `⚠` if regression signal exists for model.
Status dot: pulses for running, static for others.
Tag tabs: cycled with `t`. `/` opens filter input (filters by model name or dag_id).

**Keybinds:** `Enter` → ModelDetailScreen, `2` → ProblemsScreen, `3` → LineageScreen for selected model, `t` → cycle tag, `r` → refresh, `/` → filter

### ProblemsScreen (key `2`)

Answers: "what models are problems and why"

Two stacked sections separated by a divider, no modals:

**Section A — Active failures** (status == failed):
Columns: `model` | `tag` | `error_type` | `error_summary (80 chars)` | `upstream_caused (Y/N)`
- upstream_caused: `has_upstream_failure == True` AND own `error_message` is None or generic
- self-caused: has own non-null `error_message`

**Section B — Regression signals** (from RegressionAnalyzer):
Columns: `model` | `tag` | `signal_type` | `severity` | `description (truncated)`
Severity coloring: critical → red, warning → yellow, info → dim

**Keybinds:** `Enter` → ModelDetailScreen, `1` → ModelListScreen, `3` → LineageScreen for selected

### LineageScreen (key `3`)

Answers: "what is the full hierarchy for this model or tag"

Two sub-modes toggled with `m` / `g`:

**Model mode (`m`)** — ASCII tree, depth 4 default:
```
sources/raw_orders  (source)
└── stg_orders  (core) [view]
    └── fct_orders  (finance) [table] [grain: order_id]   ← selected
        ├── mart_revenue  (finance) [table]
        └── fct_risk_exposure  (risk) [incremental]
```
`+`/`-` expand/collapse depth. Rich markup for status colors.

**Tag/group mode (`g`)** — flat indented list grouped by DAG layer:
```
Layer 1 (sources): raw_orders, raw_payments
Layer 2 (staging): stg_orders, stg_payments
Layer 3 (facts):   fct_orders, fct_revenue_daily
Layer 4 (marts):   mart_revenue, mart_platform_usage
```
Layer inferred from node depth in the manifest DAG.

**Keybinds:** `Enter` → ModelDetailScreen, `+`/`-` → expand/collapse, `m` → model mode, `g` → tag mode, `1` → ModelListScreen, `2` → ProblemsScreen

### ModelDetailScreen (Enter from any screen)

Answers: "what is everything about this model"

5 tabs, navigated with `1`–`5` or arrow keys. No modal overlays.

| Tab | Key | Content |
|---|---|---|
| Status | `1` | run state, duration, started_at, finished_at, pod_name, warehouse, row count (current/previous/delta), bytes_scanned, dag_id, task_id, error block (full scrollable red monospace if failed), upstream dep health table |
| Structure | `2` | materialization, schema + database (full path), grain columns, all tags, config block (pretty-printed YAML, scrollable) |
| Variables + Refs | `3` | refs() table (model_name / tag / status / materialization), sources() table (source.table / database / schema), dbt vars() table (var_name / default_value — highlights "REQUIRED" if no default) |
| SQL | `4` | full compiled_sql, syntax-highlighted, scrollable, no truncation. If None: "compiled SQL not available — run dbt compile" |
| Regression | `5` | all RegressionSignals for this model, full descriptions, grain_before/grain_after as two columns, row history table (current vs previous, numeric) |

**Keybinds within detail:** `1`–`5` → switch tab, `Esc` → back, `3` → LineageScreen for this model, `r` → refresh Status tab only

---

## Config schema

```yaml
connections:
  default:
    url: http://localhost:8080        # Airflow — optional
    auth:
      type: basic
      username: admin
      password: admin
    dbt:
      manifest_path: ./target/manifest.json
      run_results_path: ./target/run_results.json
      run_results_previous_path: ./target/run_results_previous.json   # optional
      manifest_previous_path: ./target/manifest_previous.json         # optional
      dag_names:
        - dbt_finance_daily
        - dbt_marketing_daily
    snowflake:                        # entire block optional
      account: ${SNOWFLAKE_ACCOUNT}
      user: ${SNOWFLAKE_USER}
      password: ${SNOWFLAKE_PASSWORD}
      warehouse: TRANSFORM_WH
      database: prod_clone_weekly
      role: TRANSFORMER
```

**New Pydantic models added to `config.py`:** `DbtConfig`, `SnowflakeConfig`. Added as optional fields on `Connection`.

**New CLI flags:**
```
--manifest PATH      path to manifest.json (overrides config)
--run-results PATH   path to run_results.json (overrides config)
--dag TEXT           Airflow DAG ID to scan (repeatable, appends to config dag_names)
--demo               run with MockDataProvider, no external services required
```

**Env var:** `TERMINAIR_MOCK_SNOWFLAKE=1` → injects `fixtures/query_history.json` instead of connecting.

---

## Makefile additions

```makefile
dbt-demo:
    uv run python -m terminair --demo

dbt-dev:
    uv run python -m terminair \
      --manifest ./target/manifest.json \
      --run-results ./target/run_results.json
```

---

## Testing strategy

**Pytest (no external services):**

| File | Covers |
|---|---|
| `tests/dbt/test_manifest.py` | All ManifestLoader methods against fixtures — node lookup, tag index, lineage, grain extraction, ref/source/var parsing |
| `tests/dbt/test_regression.py` | All 6 signal types, severity thresholds, sort order |
| `tests/dbt/test_aggregator.py` | StateAggregator with MockDataProvider injected; `has_upstream_failure` computation |
| `tests/dbt/test_mock_data.py` | tick() transitions, row_delta_pct recomputation, all signal types represented |
| `tests/test_read_only.py` | Extended: AirflowBridge has no POST/PUT/DELETE/PATCH |

**Unchanged tests:** `test_config.py`, `test_flash.py`, `test_command_palette.py`

**Deleted tests:** `test_metrics.py`, `test_failure_heatmap.py`, `test_event_log_loader.py`

**Demo testability:** `make dbt-demo` → all 4 screens, all keybind paths, all tabs, all signal types — no external service required.

**Cannot be tested locally (documented):**
- Real Snowflake connection → bypass with `TERMINAIR_MOCK_SNOWFLAKE=1`
- Real dbt `target/` artifacts → `--manifest`/`--run-results` flags
- Kubernetes pod names → `pod_name` nullable, renders `--`
- Grain diff across real deploys → `manifest_previous.json` must be manually archived after each prod run

---

## Non-goals

- No write actions of any kind
- No dbt run triggering
- No Airflow task clears or retries
- No DAG list as primary view
- No pools, health, SLA misses, resource timeline, XCom screens
- No log streaming
- No dbt Cloud API (local artifacts only)
- No charts or sparklines (row counts are numeric text only)
- No dbt docs integration
- No schema evolution tracking beyond grain diff
