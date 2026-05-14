---
phase: 02-dbt-data-layer
plan: "04"
subsystem: dbt-data-layer
tags: [aggregator, regression, mock-data, composition-root]
dependency_graph:
  requires: [02-01, 02-02, 02-03]
  provides: [StateAggregator, RegressionAnalyzer, MockDataProvider]
  affects: [phase-04-screens]
tech_stack:
  added: []
  patterns: [composition-root, dependency-injection, tdd-red-green]
key_files:
  created:
    - terminair/dbt/aggregator.py
    - terminair/dbt/regression.py
    - terminair/dbt/mock_data.py
    - terminair/tests/dbt/test_aggregator.py
    - terminair/tests/dbt/test_regression_and_mock.py
  modified: []
decisions:
  - "StateAggregator sets dag_id='' since dag_names are unknown at this layer (resolved in Phase 4 by screens)"
  - "AirflowBridge errors caught at aggregator level so get_models() never raises"
  - "RegressionAnalyzer caches last analyze() result for signals_for_model() lookups"
metrics:
  duration: "~5 min"
  completed: "2026-05-14"
  tasks_completed: 2
  files_created: 5
---

# Phase 02 Plan 04: StateAggregator + RegressionAnalyzer + MockDataProvider Summary

StateAggregator/RegressionAnalyzer/MockDataProvider composition layer merging all Wave 1+2 dbt data sources.

## What Was Built

### Task 1: StateAggregator (`terminair/dbt/aggregator.py`)

Single composition root that calls ManifestLoader, ArtifactReader, and optional AirflowBridge/SnowflakeClient to produce `list[ModelState]`.

Key behaviors:
- `async get_models()` iterates all manifest nodes and constructs one `ModelState` per node
- Run result status `"error"` is normalized to `"failed"` (dbt outputs "error" for compile/runtime failures)
- `has_upstream_failure = any(v in ("failed","skipped") for v in upstream_statuses.values())`
- `row_delta_pct = (rows_written - rows_previous) / rows_previous * 100`; `None` if either missing or previous is 0
- `compiled_sql` populated from `node["compiled_code"]` JSON key in manifest
- AirflowBridge errors are caught with `_log.warning()`; models fall back to `pod_name=None`
- SnowflakeClient absence yields `bytes_scanned=None` for all models

### Task 2: RegressionAnalyzer (`terminair/dbt/regression.py`) and MockDataProvider (`terminair/dbt/mock_data.py`)

**RegressionAnalyzer:**
- `analyze(previous=None)` detects 6 signal types with severity thresholds:
  - `row_drop < -30%` → CRITICAL; `row_drop < -10%` → WARNING
  - `row_spike > +50%` → WARNING
  - `grain_added` (more columns) → WARNING; `grain_removed` (fewer columns) → CRITICAL
  - `upstream_schema_change` (materialization or grain changed) → WARNING
  - `new_model_no_baseline` (`rows_previous is None AND status == "success"`) → INFO
- Output sorted CRITICAL → WARNING → INFO via `_SEVERITY_ORDER` dict
- `signals_for_model(node_id)` filters cached last `analyze()` result

**MockDataProvider:**
- `async def get_models()` (no awaits) matches StateAggregator interface exactly
- 10 models: finance(3), marketing(2), core(2), platform(2), risk(1)
- Status: 2 running, 2 failed, 2 queued, 4 success
- Pre-wired signals: `stg_orders` at -25.0% (WARNING), `mart_platform_usage` at -40.67% (CRITICAL), `fct_platform_events` with `rows_previous=None` + success (INFO)
- `tick()` increments running model `duration_s` by 5.0 s each call; every 4th tick transitions the first running model to success

## TDD Gate Compliance

| Gate | Status | Commit |
|------|--------|--------|
| RED (test) — aggregator | PASS | 1e10852 |
| GREEN (feat) — aggregator | PASS | 7ac8d88 |
| RED (test) — regression + mock | PASS | d24c809 |
| GREEN (feat) — regression + mock | PASS | 4630e38 |

## Test Results

- `terminair/tests/dbt/test_aggregator.py` — 10 tests, all pass
- `terminair/tests/dbt/test_regression_and_mock.py` — 16 tests, all pass
- Full suite: 93 tests, all pass

## Deviations from Plan

### Auto-adjustments (not bugs)

**1. dag_id defaults to "" (not plan-specified mapping)**
- The plan's action section described mapping dag_id from tags ("dbt_finance_daily" etc.) but StateAggregator has no knowledge of dag→tag mapping — that's a Phase 4 screen concern.
- **Fix:** dag_id set to `""` in StateAggregator; MockDataProvider uses the full mapping inline since it owns its own fixture data.
- **Impact:** None — dag_id="" is a valid fallback per ModelState schema.

None other — plan executed closely to spec.

## Known Stubs

None — all fields produce real values from fixtures. `compiled_sql` may be `None` for fixture nodes that lack `compiled_code` in manifest.json (this is valid fixture behavior).

## Threat Flags

T-02-10 mitigated: AirflowBridge errors logged via `_log.warning(str(e)[:80])` — not surfaced to UI.

## Self-Check: PASSED

All 5 created files exist on disk. All 4 task commits verified in git log.
