# Phase 2: dbt Data Layer - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Build the `terminair/dbt/` package: seven Python modules plus five fixture files. This is the data layer that all four dbt screens will consume. No UI code in this phase — purely the data contract, logic, and fixtures.

Modules to create:
- `terminair/dbt/__init__.py`
- `terminair/dbt/manifest.py` — ManifestLoader
- `terminair/dbt/artifacts.py` — ArtifactReader
- `terminair/dbt/airflow_bridge.py` — AirflowBridge (GET only, dag_names→task scan→fuzzy match)
- `terminair/dbt/snowflake_client.py` — SnowflakeClient (bytes_scanned, mockable via DI)
- `terminair/dbt/aggregator.py` — StateAggregator (single composition root → list[ModelState])
- `terminair/dbt/regression.py` — RegressionAnalyzer (6 signal types)
- `terminair/dbt/mock_data.py` — MockDataProvider (same interface as StateAggregator, 10 models, tick())

Data classes to define (in `terminair/dbt/__init__.py` or a shared `models.py`):
- `ModelState` dataclass — full spec in design doc
- `RegressionSignal` dataclass — full spec in design doc

Fixture files to create under `terminair/dbt/fixtures/`:
- `manifest.json` — 10 models, 4 tags (finance, marketing, core, risk), realistic node structure
- `run_results.json` — 2 running, 1 self-failed, 1 upstream-failed, 2 queued, 4 success
- `run_results_previous.json` — prior run; 2 models trigger row_drop; 1 model different grain
- `manifest_previous.json` — prior manifest; 1 model different unique_key triggers grain_added
- `query_history.json` — Snowflake mock; bytes_scanned per model

</domain>

<decisions>
## Implementation Decisions

### Architecture
- StateAggregator is the single composition root — screens never call data sources directly
- MockDataProvider implements identical interface to StateAggregator (same return type: list[ModelState])
- SnowflakeClient must be injectable via dependency injection; TERMINAIR_MOCK_SNOWFLAKE=1 env var injects fixtures/query_history.json
- AirflowBridge is GET-only — zero POST/PUT/DELETE/PATCH methods (enforced by test_read_only.py later)
- All modules must be independently importable without side effects

### ManifestLoader grain extraction precedence
1. `node.config.unique_key` (list or string)
2. `node.config.partition_by.field`
3. Schema.yml tests where test name is "unique" combined with "not_null"
4. Fallback: `grain_columns = []`, signal includes "grain unknown"

### var() extraction
- Regex: `var\(['"](\w+)['"](?:,\s*([^)]+))?\)`
- Applied against `raw_sql` or `compiled_sql`
- Returns `{var_name: default_value}` or `{var_name: "REQUIRED"}` if no default

### RegressionAnalyzer signal thresholds
- row_drop: delta < -10% to -30% → warning; < -30% → critical
- row_spike: delta > +50% → warning
- grain_added: grain_columns current > previous → warning
- grain_removed: grain_columns current < previous → critical
- upstream_schema_change: upstream materialization or grain changed → warning
- new_model_no_baseline: rows_previous is None AND status == success → info
- Results sorted: critical first, then warning, then info

### MockDataProvider fixture distribution (10 models)
- 2 running (duration increments each tick)
- 1 failed (own error_message — Snowflake SQL compilation error)
- 1 failed (has_upstream_failure=True, no own error)
- 2 queued
- 4 success
- 2 models: row_delta_pct < -25% → row_drop signals
- 1 model: grain_columns differs from previous → grain_added signal
- 1 model: rows_previous is None → new_model_no_baseline signal
- Tags: finance(3), marketing(2), core(2), platform(2), risk(1)
- tick(): after 4 ticks, one running model transitions to success, row_delta_pct recomputed

### Claude's Discretion
- Internal helpers and private methods are at Claude's discretion
- Error handling: raise specific exceptions (not bare except) for callers to handle
- Fixture JSON structure must match real dbt manifest v10+ schema conventions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `terminair/config.py` — Config/Connection Pydantic models; DbtConfig will extend this pattern
- `terminair/api/models.py` — Pattern for Pydantic API response models
- `terminair/logging_utils.py` — `get_logger()` and `sanitize_error()` utilities
- `terminair/widgets/flash.py` — FlashBar pattern (not reused here, but establishes error UX)

### Established Patterns
- Pydantic v2 for all data models
- httpx for async HTTP (AirflowBridge will use this for REST API calls)
- `@dataclass` for ModelState and RegressionSignal (pure data, not Pydantic)
- All async HTTP calls use httpx; keep AirflowBridge methods async

### Integration Points
- `terminair/dbt/` is a new top-level package — needs `__init__.py`
- StateAggregator output (`list[ModelState]`) is the contract for Phase 4 screens
- MockDataProvider plugs in anywhere StateAggregator is used (same return type)
- Config extension (Phase 3) will add DbtConfig and SnowflakeConfig to Connection model

</code_context>

<specifics>
## Specific Ideas

- Canonical reference: `docs/superpowers/specs/2026-05-14-dbt-intelligence-design.md` — contains full ModelState and RegressionSignal field specifications
- Fixture manifest.json should use dbt manifest schema v10 (dbt 1.5+) node structure
- AirflowBridge fuzzy matching: use difflib.get_close_matches or simple substring matching between task_id and manifest node name
- TERMINAIR_MOCK_SNOWFLAKE=1: check env var in SnowflakeClient.__init__, load fixtures/query_history.json if set
- Unit tests for this phase go in terminair/tests/dbt/ (new subdirectory): test_manifest.py, test_regression.py, test_aggregator.py, test_mock_data.py

</specifics>

<deferred>
## Deferred Ideas

- Real Snowflake connection (INFORMATION_SCHEMA.QUERY_HISTORY) — Phase 2 only needs the interface and mock
- Kubernetes pod name resolution — pod_name is nullable, always None in fixture data
- Automated manifest_previous.json capture — manual archive documented only

</deferred>
