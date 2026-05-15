---
phase: 03-config-cli-extension
plan: 01
subsystem: ui
tags: [textual, flash, config, pydantic, pytest]

# Dependency graph
requires:
  - phase: 02-dbt-data-layer
    provides: MockDataProvider, StateAggregator, ArtifactReader, ManifestLoader
provides:
  - "_flash_warn calls in all four _build_data_provider fallback branches in app.py"
  - "test_manifest_configured_but_missing_calls_flash_warn test in test_app_demo.py"
affects: [screens, demo-mode, developer-UX]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fallback branches emit both _logger.warning (log file) and self._flash_warn (TUI) for dual-channel developer feedback"

key-files:
  created: []
  modified:
    - terminair/app.py
    - terminair/tests/test_app_demo.py

key-decisions:
  - "All four fallback branches in _build_data_provider now surface warnings to the TUI via _flash_warn in addition to the existing logger.warning calls — no fallback is silent to the developer"

patterns-established:
  - "Dual-channel warnings: _logger.warning + self._flash_warn for any condition that silently degrades data provider to MockDataProvider"

requirements-completed: [CFG-01, CFG-02, CFG-03, CFG-04, CFG-05]

# Metrics
duration: 5min
completed: 2026-05-15
---

# Phase 3 Plan 01: Config + CLI Extension Summary

**Four _build_data_provider fallback branches now emit TUI-visible FlashBar warnings via self._flash_warn(), closing CFG-05 — developers see degraded-to-demo-data warnings in the TUI, not only in log files**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-15T17:05:00Z
- **Completed:** 2026-05-15T17:10:00Z
- **Tasks:** 1 auto + 1 checkpoint:verify
- **Files modified:** 2

## Accomplishments

- Added `self._flash_warn()` calls to all four fallback branches in `_build_data_provider` (no dbt config, manifest missing, data layer error, Airflow bridge unavailable)
- Added `test_manifest_configured_but_missing_calls_flash_warn` test to `test_app_demo.py` asserting both MockDataProvider fallback and `_flash_warn` invocation with `monkeypatch.setattr`
- Verified full test suite passes: 112 tests, zero failures, all five CFG requirement IDs covered

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _flash_warn calls to all four fallback branches** - `614c58b` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `terminair/app.py` - Added four `self._flash_warn(...)` calls after each `_logger.warning` in `_build_data_provider`
- `terminair/tests/test_app_demo.py` - Added `test_manifest_configured_but_missing_calls_flash_warn` using `monkeypatch.setattr` to assert TUI warning fires

## Decisions Made

None - followed plan as specified. CFG-01 through CFG-04 were already implemented and tested; only CFG-05 (TUI-visible fallback warnings) required the additive one-liners.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 03 fully complete. All five CFG requirements (DbtConfig model, SnowflakeConfig model, Connection optional fields, CLI flags, TUI fallback warnings) are implemented and tested.
- 112 tests passing; ready for Phase 04 if applicable.

---
*Phase: 03-config-cli-extension*
*Completed: 2026-05-15*
