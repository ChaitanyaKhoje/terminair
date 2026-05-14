---
phase: 02-dbt-data-layer
plan: "01"
subsystem: dbt-data-layer
tags: [dataclasses, fixtures, dbt, models]
dependency_graph:
  requires: []
  provides:
    - terminair.dbt.ModelState
    - terminair.dbt.RegressionSignal
    - terminair.dbt.models.Severity
    - terminair/dbt/fixtures/manifest.json
    - terminair/dbt/fixtures/manifest_previous.json
    - terminair/dbt/fixtures/run_results.json
    - terminair/dbt/fixtures/run_results_previous.json
    - terminair/dbt/fixtures/query_history.json
  affects: []
tech_stack:
  added: []
  patterns:
    - dataclass with field(default_factory=...) for collection defaults
    - StrEnum for type-safe string constants (Severity)
    - compiled_sql internal field name maps from manifest compiled_code JSON key
key_files:
  created:
    - terminair/dbt/__init__.py
    - terminair/dbt/models.py
    - terminair/dbt/fixtures/manifest.json
    - terminair/dbt/fixtures/manifest_previous.json
    - terminair/dbt/fixtures/run_results.json
    - terminair/dbt/fixtures/run_results_previous.json
    - terminair/dbt/fixtures/query_history.json
  modified: []
decisions:
  - "ModelState.compiled_sql field stores manifest compiled_code JSON value — intentional rename at the data boundary"
  - "run_results.json uses dbt status 'skipped' (not 'upstream-failed') for the upstream-failure model; StateAggregator will interpret via upstream_statuses"
  - "stg_orders row delta is exactly -25.0% (boundary case) to validate threshold logic in RegressionAnalyzer"
metrics:
  duration_seconds: 252
  completed_date: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 0
---

# Phase 02 Plan 01: dbt Package Skeleton and Fixtures Summary

**One-liner:** ModelState/RegressionSignal dataclasses (30+9 fields) and five dbt v10/v5 fixture files covering 10 models with row_drop and grain_added regression triggers.

## What Was Built

Created the `terminair/dbt` package skeleton — the data contract foundation that all Wave 2+ modules will consume.

### Task 1: terminair/dbt Package with Dataclasses

- `terminair/dbt/__init__.py`: package init, no side effects, re-exports ModelState and RegressionSignal
- `terminair/dbt/models.py`: three exported symbols:
  - `Severity(StrEnum)`: INFO / WARNING / CRITICAL
  - `ModelState`: 30-field dataclass; 10 required positional fields, 10 optional scalar (None default), 10 collection fields (list/dict with default_factory)
  - `RegressionSignal`: 9-field dataclass covering all 6 signal types
- Key design note: `ModelState.compiled_sql` is the internal Python field; its value comes from the manifest JSON key `compiled_code`. The rename is intentional — the artifact schema uses dbt's convention, the data model uses SQL-conventional naming.

### Task 2: Five Fixture JSON Files

All fixtures live in `terminair/dbt/fixtures/`. All use `raw_code`/`compiled_code` — never `raw_sql`/`compiled_sql`.

| File | Schema | Purpose |
|------|--------|---------|
| manifest.json | dbt manifest v10 | 10 models, 4 tags, current grain state |
| manifest_previous.json | dbt manifest v10 | Same 10 models; fct_revenue_daily unique_key changed to list (triggers grain_added) |
| run_results.json | dbt run-results v5 | 2 running / 1 error / 1 skipped / 2 queued / 4 success |
| run_results_previous.json | dbt run-results v5 | All 10 success; stg_orders -25%, mart_platform_usage -40.7% (row_drop triggers) |
| query_history.json | custom flat dict | 10 model names → bytes_scanned integers |

**Tag distribution:** finance(3), marketing(2), core(2), platform(2), risk(1)

**Lineage wired in fixtures:**
- stg_orders, stg_payments → fct_orders, fct_revenue_daily → mart_finance_summary
- stg_campaign_events → fct_campaign_attribution
- stg_orders → fct_platform_events → mart_platform_usage
- fct_orders → fct_risk_exposure

## Verification Results

All success criteria met:

- `from terminair.dbt import ModelState, RegressionSignal` — imports cleanly, no side effects
- ModelState: 30 fields confirmed (includes `compiled_sql`, not `compiled_code`)
- RegressionSignal: 9 fields confirmed
- Severity: INFO/WARNING/CRITICAL values confirmed
- All 5 fixture files parse as valid JSON
- Zero occurrences of `raw_sql` or `compiled_sql` in fixtures/
- run_results.json: 2 running, 1 error, 1 skipped, 2 queued, 4 success
- manifest_previous.json: fct_revenue_daily unique_key `["revenue_date", "region_id"]` vs current `"revenue_date"`
- Row drop triggers: stg_orders -25.0%, mart_platform_usage -40.7%
- Existing test suite: 15 passed (0 failures)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3140503 | feat(02-01): create terminair/dbt package with ModelState and RegressionSignal dataclasses |
| 2 | 1fe644f | feat(02-01): create five dbt fixture JSON files in terminair/dbt/fixtures/ |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan creates data contracts and fixture files only. No UI data wiring involved.

## Self-Check: PASSED

- terminair/dbt/__init__.py: FOUND
- terminair/dbt/models.py: FOUND
- terminair/dbt/fixtures/manifest.json: FOUND
- terminair/dbt/fixtures/manifest_previous.json: FOUND
- terminair/dbt/fixtures/run_results.json: FOUND
- terminair/dbt/fixtures/run_results_previous.json: FOUND
- terminair/dbt/fixtures/query_history.json: FOUND
- Commit 3140503: FOUND
- Commit 1fe644f: FOUND
