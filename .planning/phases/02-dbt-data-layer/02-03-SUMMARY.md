---
phase: 02-dbt-data-layer
plan: "03"
subsystem: api
tags: [httpx, airflow, snowflake, difflib, mock, dependency-injection, async]

requires:
  - phase: 02-01
    provides: query_history.json fixture and terminair.dbt.models types

provides:
  - AirflowBridge — async GET-only httpx client with fuzzy task→node matching
  - AirflowBridgeError — sanitized error wrapper
  - _fuzzy_match — substring-first + difflib.get_close_matches(cutoff=0.6) helper
  - SnowflakeClient — bytes_scanned per model with env-var mock and DI fixture_path

affects:
  - 02-04 (StateAggregator uses both clients as injected dependencies)
  - 02-05 (MockDataProvider must implement same interface signatures)
  - 05 (test_read_only.py verifies no write methods on AirflowBridge)

tech-stack:
  added: []
  patterns:
    - "GET-only httpx.AsyncClient with build_auth() — no manual BasicAuth construction"
    - "fuzzy match: substring-first, then difflib.get_close_matches(cutoff=0.6)"
    - "env-var boolean: os.environ.get().strip().lower() in {1,true,yes,on}"
    - "DI mock: fixture_path kwarg in constructor for test overrides"
    - "sanitize_error() in httpx error handler — strips Authorization headers"

key-files:
  created:
    - terminair/dbt/airflow_bridge.py
    - terminair/dbt/snowflake_client.py
    - terminair/tests/dbt/test_airflow_bridge.py
    - terminair/tests/dbt/test_snowflake_client.py
  modified: []

key-decisions:
  - "AirflowBridge raises AirflowBridgeError per-dag (not silently returning empty) — callers handle errors"
  - "get_task_statuses uses matched_name (short name) as key, not full node_id — StateAggregator resolves"
  - "_STATE_MAP normalises Airflow states: upstream_failed→failed, none→queued"
  - "SnowflakeClient real connection deferred to v2; v1 returns None when mock disabled"

patterns-established:
  - "Rule: AirflowBridge source must have zero self._client.post/put/delete/patch — verified by source scan test"
  - "Rule: close() must exist and be async — verified by test_close_method_exists"
  - "Rule: module-level imports have no file-read side effects — verified by test_no_module_level_file_read"

requirements-completed: [DAT-03, DAT-04]

duration: 35min
completed: "2026-05-14"
---

# Phase 2 Plan 03: AirflowBridge and SnowflakeClient Summary

**Async GET-only AirflowBridge with difflib fuzzy matching and injectable SnowflakeClient with env-var mock backed by query_history.json**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-14T21:23:48Z
- **Completed:** 2026-05-14T21:59:20Z
- **Tasks:** 2 (each with RED+GREEN TDD cycle)
- **Files created:** 4 (2 source + 2 test)
- **Files modified:** 0

## Accomplishments

- AirflowBridge: async GET-only httpx client using build_auth(); fuzzy-matches task_ids to node names via substring-first then difflib; sanitizes httpx errors via sanitize_error() before raising AirflowBridgeError
- SnowflakeClient: env-var controlled mock (TERMINAIR_MOCK_SNOWFLAKE in {1,true,yes,on}) loads query_history.json; fixture_path kwarg enables DI in tests; real Snowflake deferred to v2
- 20 new tests added across both modules; full test suite (67 tests) passes

## Task Commits

Each task was committed atomically with RED → GREEN TDD cycle:

1. **Task 1: AirflowBridge RED** - `c70a57d` (test) — 11 failing tests
2. **Task 1: AirflowBridge GREEN** - `5994f92` (feat) — implementation, all 11 pass
3. **Task 2: SnowflakeClient RED** - `c02af97` (test) — 9 failing tests
4. **Task 2: SnowflakeClient GREEN** - `7867fe5` (feat) — implementation, all 9 pass

## Files Created/Modified

- `terminair/dbt/airflow_bridge.py` — AirflowBridge class, AirflowBridgeError, _fuzzy_match, _STATE_MAP
- `terminair/dbt/snowflake_client.py` — SnowflakeClient with mock/DI pattern
- `terminair/tests/dbt/test_airflow_bridge.py` — 11 tests: import, GET-only, close(), fuzzy match, instantiation
- `terminair/tests/dbt/test_snowflake_client.py` — 9 tests: import, no-mock, mock variants, DI, no side-effects

## Decisions Made

- AirflowBridge raises AirflowBridgeError (not returns empty dict) when an httpx.HTTPError occurs — per-dag granularity so caller can skip failed dags; callers wrap in try/except
- get_task_statuses returns matched_name (short name like "fct_revenue_daily") as dict key rather than full node_id — StateAggregator has the manifest and resolves to node_id
- _STATE_MAP handles all known Airflow states: upstream_failed→failed, none→queued
- SnowflakeClient real connection intentionally deferred; v1 returns None when mock disabled to avoid broken imports

## Deviations from Plan

None — plan executed exactly as written. All interface contracts, env-var patterns, and TDD flow followed verbatim.

## Issues Encountered

None.

## Threat Surface Scan

Both files implement T-02-06 (sanitize_error on httpx errors), T-02-08 (GET-only via source-scan test), and T-02-09 (fixture_path is developer-controlled). No new network endpoints or auth paths beyond what the threat model describes.

## Known Stubs

None — both clients are fully functional for their v1 scope (mock SnowflakeClient and AirflowBridge HTTP client are the intended implementations for this phase).

## Next Phase Readiness

- Both clients are ready to be injected into StateAggregator (02-04)
- AirflowBridge.get_task_statuses(dag_names, node_names) signature is stable
- SnowflakeClient.get_bytes_scanned(model_name) signature is stable
- TERMINAIR_MOCK_SNOWFLAKE=1 is safe to set in any test environment

---
*Phase: 02-dbt-data-layer*
*Completed: 2026-05-14*
