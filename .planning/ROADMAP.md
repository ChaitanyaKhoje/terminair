# Roadmap: Terminair — dbt Model Intelligence TUI

## Overview

Brownfield repositioning of an Airflow TUI into a dbt model intelligence tool. The execution order follows Approach B (horizontal layers): clean the slate first, build and fully test the dbt data layer, extend config and CLI, wire the four new screens, then lock in tests and build targets. Each phase is independently verifiable before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Cleanup** - Remove all deprecated Airflow screens, modules, and tests — clean slate for dbt work (completed 2026-05-14)
- [ ] **Phase 2: dbt Data Layer** - Build terminair/dbt/ package with full unit coverage and fixture files; no screens yet
- [ ] **Phase 3: Config + CLI Extension** - Extend config.py with DbtConfig/SnowflakeConfig and add --manifest/--run-results/--dag/--demo CLI flags
- [ ] **Phase 4: Screens** - Build all four new dbt screens wired to StateAggregator/MockDataProvider; replace app.py routing
- [ ] **Phase 5: Tests + Build** - Full test suite for the dbt layer, extend test_read_only, add Makefile targets, verify end-to-end demo mode

## Phase Details

### Phase 1: Cleanup
**Goal**: The codebase contains no Airflow screen files, Airflow-specific source modules, or tests for removed code — providing a clean foundation for dbt work
**Depends on**: Nothing (first phase)
**Requirements**: CLN-01, CLN-02, CLN-03, CLN-04
**Success Criteria** (what must be TRUE):
  1. All 16 deprecated screen files (pools, health, sla_misses, resource_timeline, xcom_viewer, dags, dag_detail, dag_deps, dag_graph, task_instances, task_history, broken_summary, recent_activity, event_log, import_errors, watchlist) are deleted from terminair/screens/
  2. All deprecated source modules (api/client.py, api/poller.py, metrics/aggregations.py, metrics/critical_path.py, metrics/error_extract.py, metrics/sparkline.py, export.py) are deleted
  3. Tests for removed code (test_metrics.py, test_failure_heatmap.py, test_event_log_loader.py) are deleted and the test suite passes cleanly with zero import errors
  4. app.py SCREENS dict and BINDINGS contain no references to any removed screen; the app starts without errors
**Plans**: 2 plans
Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Delete all deprecated Airflow screen files, API modules, metrics modules, and test files

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Update app.py, __init__.py, pyproject.toml, and test_read_only.py to remove all Airflow references

### Phase 2: dbt Data Layer
**Goal**: The terminair/dbt/ package exists with all seven modules fully implemented and tested against fixture files — screens can be written against a known-good data contract
**Depends on**: Phase 1
**Requirements**: DAT-01, DAT-02, DAT-03, DAT-04, DAT-05, DAT-06, DAT-07, FIX-01, FIX-02, FIX-03, FIX-04, FIX-05
**Success Criteria** (what must be TRUE):
  1. ManifestLoader correctly loads fixtures/manifest.json and returns node lookup, tag index, lineage tree, grain columns, refs, sources, and dbt vars for all 10 fixture models
  2. ArtifactReader reads both run_results.json and run_results_previous.json; when the previous file is absent it returns rows_previous=None without error
  3. StateAggregator merges all data sources into list[ModelState] and correctly computes has_upstream_failure by walking upstream_statuses
  4. RegressionAnalyzer detects all 6 signal types (row_drop, row_spike, grain_added, grain_removed, upstream_schema_change, new_model_no_baseline) at the correct severity thresholds, sorted critical-first
  5. MockDataProvider provides 10 models covering all status types and all signal types; tick() increments durations and transitions one running model to success after 4 ticks
**Plans**: 5 plans

Plans:
**Wave 1** *(can run in parallel)*
- [ ] 02-01-PLAN.md — Create ModelState/RegressionSignal dataclasses and all five fixture JSON files
- [ ] 02-02-PLAN.md — Implement ManifestLoader and ArtifactReader

**Wave 2** *(blocked on Wave 1: 02-01)*
- [ ] 02-03-PLAN.md — Implement AirflowBridge and SnowflakeClient

**Wave 3** *(blocked on Wave 1: 02-02, Wave 2: 02-03)*
- [ ] 02-04-PLAN.md — Implement StateAggregator, RegressionAnalyzer, and MockDataProvider

**Wave 4** *(blocked on all prior waves)*
- [ ] 02-05-PLAN.md — Create test package and all four test files; run full suite
**UI hint**: no

### Phase 3: Config + CLI Extension
**Goal**: The config schema accepts dbt and snowflake blocks; CLI flags --manifest, --run-results, --dag, and --demo work; missing manifest automatically falls back to MockDataProvider
**Depends on**: Phase 2
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05
**Success Criteria** (what must be TRUE):
  1. DbtConfig and SnowflakeConfig Pydantic models exist in config.py with all specified fields; SnowflakeConfig is fully optional and its absence does not raise any error
  2. Connection model accepts optional dbt and snowflake sub-blocks without breaking existing config loading
  3. Running `python -m terminair --demo` starts the app against MockDataProvider with no Airflow, no manifest file, and no Snowflake credentials required
  4. `--dag` flag is repeatable and appends DAG IDs to config dag_names; `--manifest` and `--run-results` override config file paths
**Plans**: TBD

### Phase 4: Screens
**Goal**: All four dbt screens exist, are navigable via number keys, share consistent filter/back/refresh/command-palette bindings, and work against both StateAggregator and MockDataProvider
**Depends on**: Phase 3
**Requirements**: SCR-01, SCR-02, SCR-03, SCR-04, SCR-05
**Success Criteria** (what must be TRUE):
  1. ModelListScreen (key 1) displays all models in a DataTable with status/model/tag/status_text/duration/rows/row_delta/dag_id columns; tag filter tabs cycle with t; / opens live text filter
  2. ProblemsScreen (key 2) shows two stacked sections — active failures with upstream-caused vs self-caused distinction, and regression signals with severity coloring (critical=red, warning=yellow, info=dim)
  3. LineageScreen (key 3) renders an ASCII tree in model mode (m) with +/- depth expansion and a flat DAG-layer list in tag/group mode (g)
  4. ModelDetailScreen (Enter from any screen) provides 5 navigable tabs (Status, Structure, Variables+Refs, SQL, Regression) with full compiled SQL scrollable and no modal overlays
  5. All screens respond consistently to /, Esc, r, :, and q; pressing Esc from any detail screen returns to the previous screen without losing navigation position
**Plans**: TBD
**UI hint**: yes

### Phase 5: Tests + Build
**Goal**: The dbt package has comprehensive pytest coverage, test_read_only.py covers AirflowBridge, Makefile has dbt-demo and dbt-dev targets, and `make dbt-demo` exercises all four screens end-to-end without any external service
**Depends on**: Phase 4
**Requirements**: TST-01, TST-02, TST-03, TST-04, TST-05, BLD-01, BLD-02, BLD-03
**Success Criteria** (what must be TRUE):
  1. tests/dbt/test_manifest.py covers all ManifestLoader methods: grain extraction precedence, var() regex, and lineage traversal all pass against fixture data
  2. tests/dbt/test_regression.py covers all 6 signal types with correct severity thresholds and verifies results are sorted critical-first
  3. tests/dbt/test_aggregator.py and tests/dbt/test_mock_data.py cover has_upstream_failure computation and tick() state transitions respectively
  4. tests/test_read_only.py extended: AirflowBridge has zero POST/PUT/DELETE/PATCH methods (same enforcement as original AirflowClient test)
  5. `make dbt-demo` starts successfully and all 4 screens, all keybind paths, all 5 ModelDetailScreen tabs, and all regression signal types are reachable with no external service
  6. Dockerfile exists and builds successfully; mounts local target/ directory and accepts AIRFLOW_URL env var
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Cleanup | 2/2 | Complete   | 2026-05-14 |
| 2. dbt Data Layer | 0/5 | Not started | - |
| 3. Config + CLI Extension | 0/TBD | Not started | - |
| 4. Screens | 0/TBD | Not started | - |
| 5. Tests + Build | 0/TBD | Not started | - |
