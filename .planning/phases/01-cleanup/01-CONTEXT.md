# Phase 1: Cleanup - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Remove all deprecated Airflow screens, Airflow-specific source modules, and tests for removed code from the terminair codebase. This phase delivers a clean Python package with no references to the old Airflow TUI layer — all imports, SCREENS dict entries, BINDINGS, and test files for removed code are gone.

Files to delete:
- terminair/screens/pools.py, health.py, sla_misses.py, resource_timeline.py, xcom_viewer.py, dags.py, dag_detail.py, dag_deps.py, dag_graph.py, task_instances.py, task_history.py, broken_summary.py, recent_activity.py, event_log.py, import_errors.py, watchlist.py
- terminair/api/client.py, api/poller.py
- terminair/metrics/aggregations.py, metrics/critical_path.py, metrics/error_extract.py, metrics/sparkline.py
- terminair/export.py
- terminair/tests/test_metrics.py, tests/test_failure_heatmap.py, tests/test_event_log_loader.py

Files to update:
- terminair/app.py — remove all imports, SCREENS dict entries, and BINDINGS for removed screens
- terminair/__init__.py — remove any references to removed modules
- pyproject.toml — update description if still mentions Airflow

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Delete files entirely (not archive/stub). Clean all import chains. After deletion, the test suite (test_config.py, test_flash.py, test_command_palette.py, test_read_only.py) must pass with zero import errors.

</decisions>

<code_context>
## Existing Code Insights

### Files to Delete
- terminair/screens/ — 16 screen files targeting Airflow observability
- terminair/api/client.py (AirflowClient), api/poller.py
- terminair/metrics/ — 4 metric modules (aggregations, critical_path, error_extract, sparkline)
- terminair/export.py
- terminair/tests/ — test_metrics.py, test_failure_heatmap.py, test_event_log_loader.py

### Files to Update
- terminair/app.py — imports all removed screens; SCREENS dict and BINDINGS reference them all
- terminair/__init__.py — check for re-exports of removed modules

### Files to Keep Unchanged
- terminair/widgets/ — filter_input.py, flash.py, help_overlay.py, command_palette.py, box_plot.py
- terminair/themes/ — dark.py, light.py
- terminair/tests/ — conftest.py, test_config.py, test_flash.py, test_command_palette.py, test_read_only.py
- terminair/api/models.py, api/auth/__init__.py
- terminair/config.py, cli.py, logging_utils.py, __main__.py

</code_context>

<specifics>
## Specific Ideas

- After deletion, app.py should still boot — it will have an empty SCREENS dict and minimal BINDINGS (just quit, escape, refresh, command palette) until Phase 4 adds the new dbt screens
- test_read_only.py currently tests AirflowClient — after deletion it will test nothing specific; leave the file skeleton for Phase 5 to extend for AirflowBridge
- pyproject.toml description should be updated to reflect dbt TUI (not Airflow TUI)

</specifics>

<deferred>
## Deferred Ideas

None — cleanup scope is fully specified.

</deferred>
