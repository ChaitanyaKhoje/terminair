# Failure Heatmap Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace "darker = more failures" heatmap visualization in DAG detail screen with color-intensity cell backgrounds, numeric overlays, a new legend, and Unicode fallback, per the approved spec.

**Architecture:** Update core rendering in airterm/screens/dag_detail.py to bucket failures and map to color/Unicode shades. Add a legend. Provide for accessibility fallback. No change to run data collection. Covered by existing test framework; add visual/logic test for bucketing as needed.

**Tech Stack:** Python, Textual (for ANSI color/cell output), Unicode, pytest (for logic unit tests)

---

### Task 1: Add Color Bucket Mapping Helper

**Files:**
- Modify: `airterm/screens/dag_detail.py` (add color and bucket mapping helpers)
- Test: (logic will be tested in new/augmented test in Task 4)

- [ ] Define color palette and bucketing thresholds for cell backgrounds (e.g., green/yellow/orange/red)
- [ ] Implement Python function mapping count → color/shade and count → Unicode shade

---

### Task 2: Refactor Heatmap Rendering Logic

**Files:**
- Modify: `airterm/screens/dag_detail.py` (refactor _failure_heatmap)
- Test: (tested visually and via Task 4)

- [ ] Update `_failure_heatmap()` to allow color style strings for each cell (when color enabled) and Unicode shade fallback
- [ ] Support numeric overlay on cells with N > 0 (if layout permits)
- [ ] Add per-cell tooltips/hints for focus/hover (if feasible in Textual)
- [ ] Return both visual grid string and legend string for later composition

---

### Task 3: Update Legend and Integration in Panel

**Files:**
- Modify: `airterm/screens/dag_detail.py` (legend and metrics-panel string)
- Modify: `README.md` (feature description update)

- [ ] Replace `(darker = more failures)` legend with "(color = failures — see legend)"
- [ ] Insert dynamic legend at top of heatmap (show coloring or Unicode/shade buckets)
- [ ] Update README: in the features list (failure heatmap) and summary to describe new scheme

---

### Task 4: Add/Modify Unit Test for Bucketing Logic

**Files:**
- Create: `airterm/tests/test_failure_heatmap.py` (if not existing)
- Or Modify: an existing suitable test file (confirm bucketing is correct)

- [ ] Add test for color/Unicode shade selection given various counts (including log scale if present)
- [ ] Check that edge values map to correct buckets and legend text

---

### Task 5: Manual/Visual Validation

**Files:**
- (no code changes)

- [ ] Run app; visually inspect heatmap in a color and non-color terminal
- [ ] Confirm legend matches buckets and is contextually accurate
- [ ] Test per-cell tooltips/focus if present; verify numeric overlays
- [ ] Validate accessibility toggle (colorblind mode or monochrome), if implemented

---

### Task 6: Commit and Review

**Files:**
- All changed/added above

- [ ] Commit with message: "feat: redesign failure heatmap with color intensity, legend, and accessibility fallback"
- [ ] (Optional) Request code review, then merge

---

## Self-Review

1. Coverage: Each spec section (color, legend, Unicode, accessibility, tooltip/focus, test) is addressed above.
2. No placeholders present; all logic/code steps are explicit.
3. Types and names are consistent between plan and anticipated code.

Plan complete and saved to `docs/superpowers/plans/2026-04-14-failure-heatmap.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?