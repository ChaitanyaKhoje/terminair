# Phase 5: Tests + Build - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — tests, Makefile targets, Dockerfile pre-implemented)

<domain>
## Phase Boundary

Extend test coverage, verify Makefile build targets, and validate Dockerfile. All primary artifacts exist:
- `terminair/tests/dbt/` — test_manifest.py, test_aggregator.py, test_regression_and_mock.py, test_artifacts.py, test_airflow_bridge.py, test_snowflake_client.py
- `terminair/tests/test_read_only.py` — stub exists; AirflowBridge check not yet implemented
- `Makefile` — dbt-demo and dbt-dev targets already defined
- `Dockerfile` — exists (316B — likely a stub)

This phase audits each success criterion and closes gaps.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and existing test patterns to guide decisions.

Key gaps to investigate during research:
- Does test_read_only.py actually assert AirflowBridge has zero write methods?
- Do the dbt test files cover all required scenarios (6 signal types, grain precedence, lineage traversal, tick() transitions)?
- Does `make dbt-demo` actually launch the TUI?
- Does the Dockerfile build successfully?

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `terminair/tests/dbt/` — existing dbt test files with patterns to follow
- `terminair/tests/test_read_only.py` — stub with comment about AirflowBridge
- `terminair/tests/conftest.py` — shared fixtures
- `Makefile` — dbt-demo/dbt-dev targets already defined
- `Dockerfile` — exists, may need verification or extension

### Established Patterns
- pytest with no mocking frameworks (monkeypatch only)
- uv run pytest for test execution
- Fixture JSON files in terminair/tests/dbt/fixtures/

### Integration Points
- AirflowBridge in terminair/dbt/airflow_bridge.py — test_read_only.py needs to assert no write methods
- MockDataProvider → all 4 screens testable via --demo flag

</code_context>

<specifics>
## Specific Ideas

- test_read_only.py: add same-pattern assertion as the original AirflowClient test but for AirflowBridge
- Dockerfile: verify it builds; if stub, extend to production-ready

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
