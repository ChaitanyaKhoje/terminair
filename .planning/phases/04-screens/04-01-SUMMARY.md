---
phase: 04-screens
plan: "01"
subsystem: screens
tags: [screens, dbt, tui, scr-01, scr-03, scr-04]
dependency_graph:
  requires: []
  provides: [SCR-01, SCR-03, SCR-04]
  affects: [terminair/screens/model_list.py, terminair/screens/lineage.py, terminair/screens/detail.py]
tech_stack:
  added: []
  patterns: [set_interval clock tick, VerticalScroll scroll pane, TabbedContent key bindings]
key_files:
  created: []
  modified:
    - terminair/screens/model_list.py
    - terminair/screens/lineage.py
    - terminair/screens/detail.py
decisions:
  - "Clock header and data statusbar update on completely separate paths: set_interval fires _update_header only; _render() fires _update_statusbar only"
  - "_depth=4 is the correct default to show root + 4 child levels as required by SCR-03"
  - "Tab IDs tab-1 through tab-5 are Textual auto-assigned in compose() order — no explicit id needed on TabPane"
  - "Binding keys 1-5 shadow screen navigation keys while ModelDetailScreen is active — intentional per SCR-04"
metrics:
  duration: "~7 min"
  completed: "2026-05-15T21:17:09Z"
  tasks_completed: 3
  files_modified: 3
---

# Phase 04 Plan 01: Screen Polish (SCR-01, SCR-03, SCR-04) Summary

**One-liner:** Surgical edits to three dbt screen files — connection+clock header and regression statusbar in ModelListScreen, 4-hop lineage default, and 1-5 tab switching with scrollable SQL pane in ModelDetailScreen.

## What Was Built

Three targeted screen modifications to close the remaining gaps between pre-implemented screen files and Phase 4 success criteria:

**SCR-01 — ModelListScreen header and statusbar:**
- Added `RegressionAnalyzer` import
- Added `#model-list-status` Static to compose() and CSS
- Added `_update_header()` — fires every 1s via set_interval, updates only `#model-list-header` with `"dbt models | {url} | {clock}"`
- Added `_update_statusbar()` — fires in `_render()`, shows `"{N} models | {M} regression warnings"`
- Clock path and data path are fully decoupled: no cross-calling

**SCR-03 — LineageScreen default depth:**
- Changed `self._depth = 3` to `self._depth = 4` in `__init__`
- First render now shows root + 4 child levels

**SCR-04 — ModelDetailScreen tab bindings and SQL scroll:**
- Added `VerticalScroll` to `textual.containers` import
- Added 5 tab-switching `Binding` entries (keys 1-5, show=False to keep footer clean)
- Replaced SQL `TabPane` single-arg form with context-manager wrapping `VerticalScroll(id="detail-sql-scroll")`
- Added `#detail-sql-scroll { height: 1fr }` CSS
- Added `action_switch_tab()` method setting `TabbedContent.active`
- `query_one("#detail-sql", Static)` in `_render()` continues to work through VerticalScroll tree

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ModelListScreen — header and statusbar | 4238a60 | terminair/screens/model_list.py |
| 2 | LineageScreen — default depth to 4 | ec68565 | terminair/screens/lineage.py |
| 3 | ModelDetailScreen — tab bindings + SQL scroll | 9af73bc | terminair/screens/detail.py |

## Verification

All 112 tests passed after each task:
```
uv run pytest terminair/tests/ -q --tb=short
112 passed in 0.16s
```

Grep gates all confirmed:
- `_depth = 4` in lineage.py
- `VerticalScroll` in detail.py (import + usage)
- `action_switch_tab` in detail.py (5 Bindings + 1 method)
- `model-list-status` in model_list.py (CSS + Static + update call)
- `set_interval` in model_list.py (on_mount, exactly 1 line)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data paths are wired. `_update_header()` reads live config URL, `_update_statusbar()` runs RegressionAnalyzer on real model data.

## Threat Flags

None — threats T-04-01, T-04-02, T-04-03 were pre-accepted in the plan's threat model. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

Files exist:
- terminair/screens/model_list.py: FOUND
- terminair/screens/lineage.py: FOUND
- terminair/screens/detail.py: FOUND

Commits exist:
- 4238a60: FOUND
- ec68565: FOUND
- 9af73bc: FOUND
