---
status: partial
phase: 04-screens
source: [04-VERIFICATION.md]
started: 2026-05-15T00:00:00Z
updated: 2026-05-15T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live TUI smoke test — all 5 SCR requirements
expected: All 4 screens navigable, clock ticking, tag filter cycles with t, regression statusbar shows, tab keys 1-5 switch tabs in detail view, SQL pane scrolls, Esc returns to prior screen
result: [pending]

Command to run: `uv run python3 -m terminair --demo`

Checklist from 04-02-PLAN.md Task 2:
- [ ] Press 1 → ModelListScreen loads with model count in footer and regression warnings in statusbar
- [ ] Clock in header ticks every second (UTC)
- [ ] Press t → tag filter cycles through tags
- [ ] Press / → filter bar opens; type to filter; Esc clears
- [ ] Press 2 → ProblemsScreen shows failures and regression signals sections
- [ ] Press 3 → LineageScreen shows ASCII tree at 4-hop depth
- [ ] Press + / - → depth expands/contracts
- [ ] Press m → model mode; press g → group mode
- [ ] Press Enter on a model → ModelDetailScreen opens
- [ ] Press 1-5 → tabs switch (Status, Structure, Variables+Refs, SQL, Regression)
- [ ] In SQL tab → compiled SQL is scrollable (not truncated)
- [ ] Press Esc → returns to previous screen at same position
- [ ] Press : → command palette opens
- [ ] Press q → quits cleanly

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
