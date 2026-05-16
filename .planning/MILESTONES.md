# Milestones

## v1.0 dbt Model Intelligence TUI (Shipped: 2026-05-16)

**Phases completed:** 6 phases, 12 plans, 18 tasks

**Key accomplishments:**

- 26 Airflow-specific screen, API, metrics, export, and test files deleted from terminair/ — codebase is now a clean Python package with no Airflow TUI layer
- app.py rewritten from 1065 to ~170 lines — all Airflow imports, SCREENS, loader methods, and action methods removed; TerminairApp boots cleanly with empty SCREENS and 5 bindings
- One-liner:
- One-liner:
- Async GET-only AirflowBridge with difflib fuzzy matching and injectable SnowflakeClient with env-var mock backed by query_history.json
- RegressionAnalyzer:
- One-liner:
- Four _build_data_provider fallback branches now emit TUI-visible FlashBar warnings via self._flash_warn(), closing CFG-05 — developers see degraded-to-demo-data warnings in the TUI, not only in log files
- One-liner:
- 112 tests pass and all three screen modules import cleanly after Plan 01 gap fixes — Phase 4 verified and ready for Phase 5.
- Split test_regression_and_mock.py into two files, added upstream_schema_change test, wired AirflowBridge read-only contract, and made Dockerfile CMD conditional on $AIRFLOW_URL — 113 tests passing.
- Three previously-silent regression signal types (grain_added, grain_removed, upstream_schema_change) are now reachable in the TUI via get_previous_models() on both StateAggregator and MockDataProvider, wired through all three screen _load_models() overrides; ModelListScreen clock now renders on first mount

---
