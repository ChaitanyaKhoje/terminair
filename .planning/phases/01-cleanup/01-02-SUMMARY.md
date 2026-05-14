---
phase: 01-cleanup
plan: 02
subsystem: infra
tags: [cleanup, airflow, app-rewrite, python]

# Dependency graph
requires:
  - "01-01: Deleted Airflow screen, API, and metrics files"
provides:
  - "Clean TerminairApp with empty SCREENS dict and minimal BINDINGS"
  - "terminair/__init__.py docstring describes dbt model intelligence TUI"
  - "pyproject.toml description updated to dbt model intelligence"
  - "test_read_only.py skeleton ready for Phase 5 AirflowBridge tests"
affects:
  - 01-cleanup
  - 02-dbt-data-layer
  - 04-screens

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Minimal TerminairApp: empty SCREENS, 5 BINDINGS, no Airflow dependencies"

key-files:
  created: []
  modified:
    - "terminair/app.py (891 lines removed, rewritten to ~170 lines)"
    - "terminair/__init__.py (docstring updated)"
    - "pyproject.toml (description field updated)"
    - "terminair/tests/test_read_only.py (replaced with skeleton)"

key-decisions:
  - "app.py rewritten as complete file replacement (scope of changes spanned full 1065 lines)"
  - "_schedule_live_reload simplified to no-op pass (no screens to reload yet)"
  - "cli.py not modified — description update is out of scope for this plan (cli.py references kept)"

patterns-established: []

requirements-completed:
  - CLN-04

# Metrics
duration: ~9 min
completed: 2026-05-14
---

# Phase 01 Plan 02: Cleanup - Remove Airflow References from app.py Summary

**app.py rewritten from 1065 to ~170 lines — all Airflow imports, SCREENS, loader methods, and action methods removed; TerminairApp boots cleanly with empty SCREENS and 5 bindings**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-14T19:30:43Z
- **Completed:** 2026-05-14T19:40:24Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Rewrote terminair/app.py: removed 14 screen imports, 2 API imports, all metric imports; emptied SCREENS dict; reduced BINDINGS from 14 to 5; removed ~20 loader/action methods and on_mount/_init_app
- Updated terminair/__init__.py docstring from Airflow to dbt model intelligence TUI
- Updated pyproject.toml description from Airflow to dbt model intelligence TUI
- Replaced test_read_only.py with a skeleton placeholder — AirflowClient import removed; Phase 5 will extend it for AirflowBridge

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite app.py** - `d44185d` (feat)
2. **Task 2: Update __init__.py, pyproject.toml, test_read_only.py** - `6ca128d` (chore)

## Files Created/Modified

- `terminair/app.py` — rewritten (891 lines removed, 14 screen imports gone, SCREENS={}, 5 bindings, no Airflow refs)
- `terminair/__init__.py` — docstring updated to dbt model intelligence TUI
- `pyproject.toml` — description field updated to dbt model intelligence TUI
- `terminair/tests/test_read_only.py` — replaced with skeleton (no AirflowClient import)

## Decisions Made

- Rewrote app.py as a complete file (not a patch) — the scope of changes touched every section of the 1065-line file
- `_schedule_live_reload` simplified to `pass` — no screens to reload yet; Phase 4 will restore this when dbt screens are added
- `cli.py` was not modified — its help text description is out of scope for this plan

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `action_refresh` is a `pass` no-op — intentional; Phase 4 will implement per-screen reload logic when dbt screens exist
- `_schedule_live_reload` is a `pass` no-op — intentional; same reason

These stubs do not prevent the plan's goal (import clean startup) and are explicitly expected by the plan spec.

## Self-Check: PASSED

- Verified: `python3 -c "import terminair.app"` exits 0 → OK
- Verified: `grep -n "from terminair.api.client\|from terminair.screens\|from terminair.metrics" terminair/app.py` → zero lines
- Verified: `grep -n "SCREENS" terminair/app.py` → `SCREENS = {}` (empty dict)
- Verified: 5 Binding() instances in app.py (plus 1 import line = 6 total grep hits)
- Verified: `grep "dbt model intelligence" terminair/__init__.py` → 1 match
- Verified: `grep "dbt model intelligence" pyproject.toml` → 1 match
- Verified: `grep "AirflowClient" terminair/tests/test_read_only.py` → zero lines
- Verified: `python3 -m terminair --help` → exits 0 without ImportError
- Verified: `python3 -m pytest terminair/tests/ -v` → 15 passed, 0 errors
- Verified: Commits `d44185d` and `6ca128d` exist in git log

---
*Phase: 01-cleanup*
*Completed: 2026-05-14*
