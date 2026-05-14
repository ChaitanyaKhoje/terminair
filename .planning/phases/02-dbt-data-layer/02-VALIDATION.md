---
phase: 2
slug: dbt-data-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest terminair/tests/dbt/ -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest terminair/tests/ -v` |
| **Estimated runtime** | ~2 seconds (unit tests, no I/O) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest terminair/tests/dbt/ -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest terminair/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-T1 | 02-01 | 1 | FIX-01..05 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py::test_fixture_loads -x` | ❌ Wave 0 | ⬜ pending |
| 02-01-T2 | 02-01 | 1 | FIX-01..05 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py::test_fixture_loads -x` | ❌ Wave 0 | ⬜ pending |
| 02-02-T1 | 02-02 | 1 | DAT-01 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 02-02-T2 | 02-02 | 1 | DAT-02 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py::test_missing_previous_graceful -x` | ❌ Wave 0 | ⬜ pending |
| 02-03-T1 | 02-03 | 2 | DAT-03 | unit | `.venv/bin/python -m pytest terminair/tests/test_read_only.py -x` | ✅ exists | ⬜ pending |
| 02-03-T2 | 02-03 | 2 | DAT-04 | unit | `.venv/bin/python -c "from terminair.dbt.snowflake_client import SnowflakeClient; print('OK')"` | ❌ Wave 0 | ⬜ pending |
| 02-04-T1 | 02-04 | 3 | DAT-05 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_aggregator.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 02-04-T2 | 02-04 | 3 | DAT-06, DAT-07 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_regression.py terminair/tests/dbt/test_mock_data.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 02-05-T1 | 02-05 | 4 | DAT-01, DAT-02, DAT-06 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py terminair/tests/dbt/test_regression.py -v` | ❌ Wave 0 | ⬜ pending |
| 02-05-T2 | 02-05 | 4 | DAT-05, DAT-07 | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_aggregator.py terminair/tests/dbt/test_mock_data.py -v` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `terminair/tests/dbt/__init__.py` — empty file, required for pytest discovery under `testpaths = ["terminair/tests"]`
- [ ] `terminair/dbt/fixtures/` directory with 5 fixture JSON files (created in Wave 1 plans 02-01)
- [ ] `terminair/tests/dbt/test_manifest.py` — covers DAT-01, DAT-02, FIX-01..05 (created in Wave 4 plan 02-05)
- [ ] `terminair/tests/dbt/test_regression.py` — covers DAT-06 (created in Wave 4 plan 02-05)
- [ ] `terminair/tests/dbt/test_aggregator.py` — covers DAT-05 (created in Wave 4 plan 02-05)
- [ ] `terminair/tests/dbt/test_mock_data.py` — covers DAT-07 (created in Wave 4 plan 02-05)

*Wave 0 items are created by the phase plans themselves — no pre-execution scaffolding needed since tests and implementations land in the same phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AirflowBridge connects to local Airflow demo stack | DAT-03 | Requires live Airflow instance | Run `make airflow-up` then `python3 -c "from terminair.dbt.airflow_bridge import AirflowBridge; import asyncio; b = AirflowBridge(['example_dag'], 'http://localhost:8080', 'admin', 'admin'); print(asyncio.run(b.get_task_statuses()))"` |
| TERMINAIR_MOCK_SNOWFLAKE=1 injects fixture data | DAT-04 | Requires env var + fixture path resolution | `TERMINAIR_MOCK_SNOWFLAKE=1 python3 -c "from terminair.dbt.snowflake_client import SnowflakeClient; c = SnowflakeClient(None); print(c.get_bytes_scanned('model.project.fct_test'))"` |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covered by plan 02-01 (fixtures) and plan 02-05 (test files)
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter after sign-off

**Approval:** pending
