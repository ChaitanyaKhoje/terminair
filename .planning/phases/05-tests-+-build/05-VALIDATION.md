---
phase: 05
slug: tests-build
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-05-15
---

# Phase 05 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Quick run command** | `uv run pytest terminair/tests/ -q --tb=short` |
| **Full suite command** | `uv run pytest terminair/tests/ -v --tb=short` |
| **Estimated runtime** | ~1 second |

## Sampling Rate

- **After every task commit:** Run `uv run pytest terminair/tests/ -q --tb=short`
- **Before verification:** Full suite must be green

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Automated Command | Status |
|---------|------|------|-------------|-------------------|--------|
| 05-01-01 | 01 | 1 | TST-02, TST-04 | `uv run pytest terminair/tests/dbt/test_regression.py terminair/tests/dbt/test_mock_data.py -v` | ⬜ pending |
| 05-01-02 | 01 | 1 | TST-05 | `uv run pytest terminair/tests/test_read_only.py -v` | ⬜ pending |
| 05-01-03 | 01 | 1 | BLD-03 | `docker build -t terminair-test . && echo BUILD_OK` | ⬜ pending |
| 05-01-04 | 01 | 1 | TST-01..05, BLD-01..03 | `uv run pytest terminair/tests/ -q --tb=short` | ⬜ pending |

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make dbt-demo` launches TUI | BLD-01 | Requires terminal TUI | Run `make dbt-demo`; confirm all 4 screens reachable |
| Docker container runs demo | BLD-03 | Requires Docker | `docker run --rm terminair-test`; confirm startup |

## Validation Architecture (from RESEARCH.md)

4 targeted changes: split test_regression_and_mock.py into test_regression.py + test_mock_data.py (adding upstream_schema_change coverage), extend test_read_only.py, fix Dockerfile CMD.
