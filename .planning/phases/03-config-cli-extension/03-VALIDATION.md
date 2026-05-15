---
phase: 03
slug: config-cli-extension
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-05-15
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest terminair/tests/test_app_demo.py -v` |
| **Full suite command** | `uv run pytest terminair/tests/ -v --tb=short` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest terminair/tests/test_app_demo.py -v`
- **After every plan wave:** Run `uv run pytest terminair/tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CFG-05 | T-03-04 | FlashBar messages contain only path strings, no secrets | unit | `uv run pytest terminair/tests/test_app_demo.py::test_manifest_configured_but_missing_calls_flash_warn -v` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | CFG-01..05 | — | N/A | integration | `uv run pytest terminair/tests/ -v --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest + uv are installed and verified (111/111 tests passing before Phase 3 execution).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FlashBar warning visible in TUI when manifest missing | CFG-05 | Requires running live TUI | Run `python -m terminair --manifest /nonexistent.json --user admin`; confirm yellow warning in bottom bar |

---

## Validation Architecture (from RESEARCH.md)

Phase 3 has a minimal execution surface — 4 one-line additions to `app.py` and 1 new test. The existing 111-test suite provides the primary regression safety net.

**Key sampling signals:**
- After Task 1: `uv run pytest terminair/tests/test_app_demo.py -v` — 3 tests including the new flash_warn test
- After Task 2 (verification sweep): `uv run pytest terminair/tests/ -v` — full 112+ test suite
