---
phase: 04
slug: screens
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-05-15
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest terminair/tests/ -q --tb=short` |
| **Full suite command** | `uv run pytest terminair/tests/ -v --tb=short` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest terminair/tests/ -q --tb=short`
- **After every plan wave:** Run `uv run pytest terminair/tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SCR-01 | — | N/A | grep | `grep -n "count" terminair/screens/model_list.py` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | SCR-03 | — | N/A | grep | `grep -n "_depth" terminair/screens/lineage.py` | ✅ | ⬜ pending |
| 04-01-03 | 01 | 1 | SCR-04 | — | N/A | grep | `grep -n "VerticalScroll\|tab-" terminair/screens/detail.py` | ✅ | ⬜ pending |
| 04-01-04 | 01 | 1 | SCR-01..05 | — | N/A | integration | `uv run pytest terminair/tests/ -q --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest + uv installed and verified (112 tests passing before Phase 4 execution).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ModelListScreen tag filter tabs cycle with `t` | SCR-01 | Requires live TUI interaction | Run `python -m terminair --demo`; press `t` repeatedly; verify tag filter cycles |
| ModelDetailScreen 1-5 keys switch tabs | SCR-04 | Requires live TUI interaction | Open detail screen; press 1-5; verify correct tab activates |
| SQL pane scrolls with large SQL content | SCR-04 | Requires live TUI interaction | Open detail for a model with compiled SQL; verify scroll works |
| Esc from detail returns to previous screen without losing position | SCR-05 | Requires live TUI interaction | Navigate to row 10; press Enter; press Esc; verify cursor at row 10 |

---

## Validation Architecture (from RESEARCH.md)

Phase 4 gaps are surgical: 4 code changes across 3 files. The existing 112-test suite provides the primary regression safety net. Manual verification via `--demo` mode covers the TUI interaction behaviors.
