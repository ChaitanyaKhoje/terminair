---
phase: 01-cleanup
plan: 01
subsystem: infra
tags: [cleanup, airflow, deletion, python]

# Dependency graph
requires: []
provides:
  - "Clean terminair/ package with no Airflow screen or source files"
  - "terminair/screens/ directory empty and ready for dbt screens (Phase 4)"
  - "terminair/api/ contains only models.py and auth/"
  - "terminair/metrics/ directory removed"
  - "Test suite retains only 5 non-Airflow tests"
affects:
  - 01-cleanup
  - 02-dbt-data-layer
  - 04-screens

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - "terminair/screens/ (emptied)"
    - "terminair/api/ (client.py and poller.py removed)"
    - "terminair/metrics/ (directory removed entirely)"
    - "terminair/tests/ (3 Airflow test files removed)"

key-decisions:
  - "Deleted files entirely (no archiving) — clean break from Airflow TUI layer"
  - "Preserved terminair/screens/ directory as empty container for upcoming dbt screens"
  - "Preserved terminair/api/models.py and auth/ — no Airflow dependency"

patterns-established: []

requirements-completed:
  - CLN-01
  - CLN-02
  - CLN-03

# Metrics
duration: 5min
completed: 2026-05-14
---

# Phase 01 Plan 01: Cleanup - Delete Deprecated Airflow Files Summary

**26 Airflow-specific screen, API, metrics, export, and test files deleted from terminair/ — codebase is now a clean Python package with no Airflow TUI layer**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-14T09:57:00Z
- **Completed:** 2026-05-14T10:07:00Z
- **Tasks:** 2
- **Files modified:** 26 deleted

## Accomplishments
- Deleted all 16 Airflow screen files from terminair/screens/ (pools, health, sla_misses, resource_timeline, xcom_viewer, dags, dag_detail, dag_deps, dag_graph, task_instances, task_history, broken_summary, recent_activity, event_log, import_errors, watchlist)
- Deleted deprecated API modules (client.py, poller.py), all 4 metrics modules, and export.py; removed the now-empty terminair/metrics/ directory
- Deleted 3 test files for removed code (test_metrics.py, test_failure_heatmap.py, test_event_log_loader.py); 5 remaining tests are intact

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete all deprecated Airflow screen files** - `a2950b3` (chore)
2. **Task 2: Delete deprecated API, metrics, export, and test files** - `c016925` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

All changes are deletions:

- `terminair/screens/pools.py` — deleted
- `terminair/screens/health.py` — deleted
- `terminair/screens/sla_misses.py` — deleted
- `terminair/screens/resource_timeline.py` — deleted
- `terminair/screens/xcom_viewer.py` — deleted
- `terminair/screens/dags.py` — deleted
- `terminair/screens/dag_detail.py` — deleted
- `terminair/screens/dag_deps.py` — deleted
- `terminair/screens/dag_graph.py` — deleted
- `terminair/screens/task_instances.py` — deleted
- `terminair/screens/task_history.py` — deleted
- `terminair/screens/broken_summary.py` — deleted
- `terminair/screens/recent_activity.py` — deleted
- `terminair/screens/event_log.py` — deleted
- `terminair/screens/import_errors.py` — deleted
- `terminair/screens/watchlist.py` — deleted
- `terminair/api/client.py` — deleted
- `terminair/api/poller.py` — deleted
- `terminair/metrics/aggregations.py` — deleted
- `terminair/metrics/critical_path.py` — deleted
- `terminair/metrics/error_extract.py` — deleted
- `terminair/metrics/sparkline.py` — deleted
- `terminair/export.py` — deleted
- `terminair/tests/test_metrics.py` — deleted
- `terminair/tests/test_failure_heatmap.py` — deleted
- `terminair/tests/test_event_log_loader.py` — deleted

## Decisions Made
- Deleted files entirely with no archiving — the plan specifies a clean break; Airflow observability is k9s's job
- The terminair/screens/ directory was already empty on the filesystem (files existed only in git history); committed the deletions to clean the git history as well

## Deviations from Plan

None - plan executed exactly as written.

Note: terminair/screens/ directory was already empty on disk when execution started (the 16 Airflow screen files existed in git but had been removed from the filesystem earlier). The task commit properly recorded their deletion from git history.

## Issues Encountered
- The terminair/metrics/ directory had a `__pycache__` subdirectory that prevented `rmdir`. Removed `__pycache__` first, then successfully removed the directory.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Clean codebase with no Airflow-specific files; ready for Plan 01-02 (clean app.py and update pyproject.toml)
- terminair/screens/ empty and ready to receive dbt screens in Phase 4
- terminair/api/models.py and auth/ preserved for potential reuse

## Self-Check: PASSED

- Verified: `terminair/api/` contains only `models.py` and `auth/`
- Verified: `terminair/metrics/` directory does not exist
- Verified: `terminair/tests/` contains only conftest.py, test_config.py, test_flash.py, test_command_palette.py, test_read_only.py
- Verified: Commits `a2950b3` and `c016925` exist in git log

---
*Phase: 01-cleanup*
*Completed: 2026-05-14*
