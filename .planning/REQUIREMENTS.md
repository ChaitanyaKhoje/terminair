# Requirements: Terminair — dbt Model Intelligence TUI

**Defined:** 2026-05-14
**Core Value:** A developer working on dbt models can instantly see what is happening with any model, why it is a problem, and what its full lineage looks like — without leaving the terminal and without touching production data.

## v1 Requirements

### Cleanup

- [x] **CLN-01**: All deprecated Airflow screens removed (pools, health, SLA misses, resource timeline, XCom viewer, DAG list, dag_detail, dag_deps, dag_graph, task_instances, task_history, broken_summary, recent_activity, event_log, import_errors, watchlist)
- [x] **CLN-02**: All deprecated Airflow-specific modules removed (api/client.py, api/poller.py, metrics/aggregations.py, metrics/critical_path.py, metrics/error_extract.py, metrics/sparkline.py, export.py)
- [x] **CLN-03**: Tests for removed screens deleted (test_metrics.py, test_failure_heatmap.py, test_event_log_loader.py)
- [x] **CLN-04**: app.py SCREENS dict and BINDINGS cleaned to remove all deprecated screen references

### Data Layer

- [x] **DAT-01**: ManifestLoader reads manifest.json and provides node lookup, tag index, upstream/downstream deps, full lineage tree, grain column extraction, ref/source/var parsing, and config access
- [x] **DAT-02**: ArtifactReader reads run_results.json and run_results_previous.json, returns per-node status, timing, row counts, and error messages; gracefully handles missing previous file
- [x] **DAT-03**: AirflowBridge accepts dag_names list, fetches all tasks for those DAGs via Airflow REST API (GET only), fuzzy-matches task IDs to manifest node names, returns {node_id: (status, pod_name)}; pod_name nullable
- [x] **DAT-04**: SnowflakeClient returns bytes_scanned per model; entire client is mockable via dependency injection; TERMINAIR_MOCK_SNOWFLAKE=1 injects fixtures/query_history.json
- [x] **DAT-05**: StateAggregator is the single composition root — merges ManifestLoader + ArtifactReader + AirflowBridge + SnowflakeClient into list[ModelState]; computes has_upstream_failure by walking upstream_statuses
- [x] **DAT-06**: RegressionAnalyzer detects all 6 signal types (row_drop, row_spike, grain_added, grain_removed, upstream_schema_change, new_model_no_baseline) with correct severity thresholds; results sorted critical-first
- [x] **DAT-07**: MockDataProvider implements the same interface as StateAggregator; provides 10 models covering all status types, all signal types, and all tag groups; tick() increments durations and transitions one running model to success after 4 ticks

### Fixtures

- [x] **FIX-01**: fixtures/manifest.json — 10 models across 4 tags (finance, marketing, core, risk) with realistic node structure including unique_key, depends_on, compiled_sql, config
- [x] **FIX-02**: fixtures/run_results.json — current run: 2 running, 1 self-failed, 1 upstream-failed, 2 queued, 4 success
- [x] **FIX-03**: fixtures/run_results_previous.json — prior run baseline; 2 models with row counts triggering row_drop; 1 model with different grain_columns
- [x] **FIX-04**: fixtures/manifest_previous.json — prior manifest; 1 model with different unique_key to trigger grain_added
- [x] **FIX-05**: fixtures/query_history.json — Snowflake mock with bytes_scanned per model

### Screens

- [ ] **SCR-01**: ModelListScreen (key 1) — topbar with connection + clock, tag filter tabs cycled with t, text filter with /, DataTable with status/model/tag/status_text/duration/rows/row_delta/dag_id columns, bottom statusbar with counts and regression warning count
- [ ] **SCR-02**: ProblemsScreen (key 2) — two stacked sections: active failures (upstream-caused vs self-caused distinction) and regression signals (severity-colored); no modals; Enter → ModelDetailScreen
- [ ] **SCR-03**: LineageScreen (key 3) — ASCII tree model mode (4-hop depth default, +/- expand/collapse) and tag/group mode (flat list by DAG layer); toggled with m/g; Rich markup for status colors
- [ ] **SCR-04**: ModelDetailScreen (Enter from any screen) — 5 tabs (Status, Structure, Variables+Refs, SQL, Regression) navigated with 1-5 or arrow keys; full compiled SQL scrollable; no modal overlays
- [ ] **SCR-05**: All screens share consistent filter (/ to open, Esc to clear), Esc to back, r to refresh, : for command palette, q to quit

### Config + CLI

- [ ] **CFG-01**: DbtConfig Pydantic model added to config.py with manifest_path, run_results_path, run_results_previous_path, manifest_previous_path, dag_names fields; all optional
- [ ] **CFG-02**: SnowflakeConfig Pydantic model added to config.py with account, user, password, warehouse, database, role fields; entire block optional
- [ ] **CFG-03**: Connection model extended with optional dbt and snowflake fields
- [ ] **CFG-04**: CLI adds --manifest, --run-results, --dag (repeatable), --demo flags; --dag appends to config dag_names
- [ ] **CFG-05**: --demo flag wires app to MockDataProvider with no external services required; fallback triggered automatically when manifest_path missing or file not found

### Build + Demo

- [ ] **BLD-01**: Makefile adds dbt-demo target (runs with --demo flag, no Airflow needed)
- [ ] **BLD-02**: Makefile adds dbt-dev target (points at local target/ directory via --manifest and --run-results)
- [ ] **BLD-03**: Dockerfile for terminair — mounts local target/ directory and connects to a configurable Airflow URL; enables running terminair without a local Python install

### Tests

- [ ] **TST-01**: tests/dbt/test_manifest.py — all ManifestLoader methods against fixtures; grain extraction precedence; var() regex; lineage traversal
- [ ] **TST-02**: tests/dbt/test_regression.py — all 6 signal types; severity thresholds; sort order (critical first)
- [ ] **TST-03**: tests/dbt/test_aggregator.py — StateAggregator with MockDataProvider injected; has_upstream_failure computation
- [ ] **TST-04**: tests/dbt/test_mock_data.py — tick() transitions; row_delta_pct recomputation; all signal types represented
- [ ] **TST-05**: tests/test_read_only.py extended — AirflowBridge has no POST/PUT/DELETE/PATCH methods

## v2 Requirements

### Extended Data Sources

- **V2-01**: Pull artifacts from S3/GCS after each dbt run (automated artifact freshness without manual copy)
- **V2-02**: manifest_previous.json automated capture pipeline (currently requires manual archive after each prod run)
- **V2-03**: Multi-warehouse Snowflake support (currently single warehouse per connection)

### Extended Intelligence

- **V2-04**: Cross-model error clustering (group similar errors across failed models)
- **V2-05**: SLA tracking per model (P95 duration baseline + breach detection)
- **V2-06**: Feed dbt model state data to Claude/Codex for inference and recommendations

## Out of Scope

| Feature | Reason |
|---------|--------|
| Write actions of any kind | Read-only is a hard product constraint; enforced by test suite |
| dbt run triggering | Not a CI tool |
| Airflow task clears or retries | Airflow is a data source only |
| DAG list as primary view | Replaced by ModelListScreen |
| Pools, health, SLA misses, resource timeline, XCom | k9s already covers Airflow observability |
| Log streaming | Out of scope for v1 |
| dbt Cloud API | Local artifacts only |
| Charts or sparklines | Row counts are numeric text only |
| dbt docs integration | Not planned |
| Schema evolution tracking beyond grain diff | Deferred to v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLN-01 | Phase 1 | Complete |
| CLN-02 | Phase 1 | Pending |
| CLN-03 | Phase 1 | Pending |
| CLN-04 | Phase 1 | Complete |
| DAT-01 | Phase 2 | Complete |
| DAT-02 | Phase 2 | Complete |
| DAT-03 | Phase 2 | Complete |
| DAT-04 | Phase 2 | Complete |
| DAT-05 | Phase 2 | Complete |
| DAT-06 | Phase 2 | Complete |
| DAT-07 | Phase 2 | Complete |
| FIX-01 | Phase 2 | Complete |
| FIX-02 | Phase 2 | Complete |
| FIX-03 | Phase 2 | Complete |
| FIX-04 | Phase 2 | Complete |
| FIX-05 | Phase 2 | Complete |
| CFG-01 | Phase 3 | Pending |
| CFG-02 | Phase 3 | Pending |
| CFG-03 | Phase 3 | Pending |
| CFG-04 | Phase 3 | Pending |
| CFG-05 | Phase 3 | Pending |
| SCR-01 | Phase 4 | Pending |
| SCR-02 | Phase 4 | Pending |
| SCR-03 | Phase 4 | Pending |
| SCR-04 | Phase 4 | Pending |
| SCR-05 | Phase 4 | Pending |
| TST-01 | Phase 5 | Pending |
| TST-02 | Phase 5 | Pending |
| TST-03 | Phase 5 | Pending |
| TST-04 | Phase 5 | Pending |
| TST-05 | Phase 5 | Pending |
| BLD-01 | Phase 5 | Pending |
| BLD-02 | Phase 5 | Pending |
| BLD-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-14*
*Last updated: 2026-05-14 after initial definition*
