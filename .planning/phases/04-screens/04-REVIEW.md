---
phase: 04-screens
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - terminair/screens/model_list.py
  - terminair/screens/lineage.py
  - terminair/screens/detail.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-15
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three Phase 04 screen files were reviewed: `ModelListScreen` (clock header + regression statusbar), `LineageScreen` (depth 4), and `ModelDetailScreen` (1-5 tab bindings + VerticalScroll SQL pane). No import errors were found; all referenced symbols exist in the installed Textual 8.2.3 and in the project's own modules.

The most impactful findings are: (1) key bindings 1-4 on `ModelDetailScreen` silently shadow the app-level global navigation bindings, stranding users who press a number key expecting screen navigation; (2) `action_switch_tab` has no guard against an invalid tab ID, meaning a future Textual version that changes ID generation would raise an unhandled exception with no user feedback; and (3) `_update_statusbar` counts regression signals without a `previous` snapshot, so `grain_added`, `grain_removed`, and `upstream_schema_change` signals — the highest-value ones — are always zero regardless of actual state.

---

## Warnings

### WR-01: 1-4 Key Bindings on ModelDetailScreen Shadow Global Navigation

**File:** `terminair/screens/detail.py:55-59`

**Issue:** `ModelDetailScreen.BINDINGS` binds keys `1`, `2`, `3`, and `4` to `switch_tab('tab-N')`. In Textual, screen-level bindings shadow app-level bindings for the same key. `TerminairApp.BINDINGS` already uses `1` (Models), `2` (Problems), `3` (Lineage), and `4` (Detail). While on `ModelDetailScreen`, pressing any of these keys silently switches tabs instead of switching screens, breaking the global k9s-style nav model that every other screen honours.

Key `5` is the only safe binding because the app does not claim it.

**Fix:** Either use keys that do not conflict with app-level bindings (e.g., function keys, bracket keys, or letter-prefixed combos like `alt+1`), or add `priority=True` to the app-level bindings and accept that number keys switch screens everywhere — including from the detail screen:

```python
# Option A: use non-conflicting keys
Binding("[", "switch_tab('tab-1')", "Status", show=False),
Binding("]", "switch_tab('tab-2')", "Structure", show=False),
# ...

# Option B: assign explicit IDs to TabPanes so keys can use memorable names
# and document clearly that 1-4 are intentionally local to this screen
```

---

### WR-02: action_switch_tab Has No Exception Guard Against Invalid Tab IDs

**File:** `terminair/screens/detail.py:156-157`

**Issue:** `action_switch_tab` sets `TabbedContent.active = tab_id` with no `try/except`. Textual's `_watch_active` calls `ContentSwitcher.current = active`, which raises `NoMatches` when the ID does not exist. The string literals `tab-1` through `tab-5` work today because `TabbedContent._tab_counter` starts at 0 and increments once per `TabPane` in `compose()`. However: (a) no `TabPane` in `compose()` has an explicit `id=` argument, so the IDs depend entirely on Textual's auto-generation order; (b) if any future edit adds, removes, or reorders a `TabPane` in `compose()`, the hardcoded literals silently address the wrong pane or raise.

**Fix:** Assign explicit IDs to each `TabPane` in `compose()` so the binding literals are stable by construction:

```python
# In compose():
with TabbedContent(id="detail-tabs"):
    yield TabPane("Status",          Static("", id="detail-status",    classes="detail-pane"), id="tab-status")
    yield TabPane("Structure",       Static("", id="detail-structure", classes="detail-pane"), id="tab-structure")
    yield TabPane("Variables+Refs",  Static("", id="detail-refs",      classes="detail-pane"), id="tab-refs")
    with TabPane("SQL", id="tab-sql"):
        with VerticalScroll(id="detail-sql-scroll"):
            yield Static("", id="detail-sql", classes="detail-pane")
    yield TabPane("Regression",      Static("", id="detail-regression", classes="detail-pane"), id="tab-regression")

# In BINDINGS:
Binding("1", "switch_tab('tab-status')",     "Status",     show=False),
Binding("2", "switch_tab('tab-structure')",  "Structure",  show=False),
Binding("3", "switch_tab('tab-refs')",       "Refs",       show=False),
Binding("4", "switch_tab('tab-sql')",        "SQL",        show=False),
Binding("5", "switch_tab('tab-regression')", "Regression", show=False),
```

Additionally, wrap the setter in a try/except for robustness:

```python
def action_switch_tab(self, tab_id: str) -> None:
    try:
        self.query_one("#detail-tabs", TabbedContent).active = tab_id
    except Exception as e:
        self.app_typed._flash_error(f"tab switch failed: {e}")
```

---

### WR-03: Regression Statusbar Counts Are Always Zero for the Most Important Signal Types

**File:** `terminair/screens/model_list.py:161-166`

**Issue:** `_update_statusbar` calls `RegressionAnalyzer(self._models).analyze()` with no `previous` argument, which defaults to `None`. Inside `analyze()`, `prev_map` is then an empty dict, making the `grain_added`, `grain_removed`, and `upstream_schema_change` code paths unreachable — those three signal types are never generated when `previous` is `None`. Only `row_drop`, `row_spike`, and `new_model_no_baseline` can appear. Since `new_model_no_baseline` is `Severity.INFO` and filtered out by the `in ("critical", "warning")` guard, the statusbar misses `grain_removed` (which is `CRITICAL`) and `grain_added` (which is `WARNING`) entirely.

The statusbar label "N regression warnings" therefore understates risk in any scenario where grain changes occur.

**Fix:** The `StateAggregator` or data provider should expose a `get_previous_models()` method (or return both current and previous snapshots together). If that is not yet implemented, document the limitation explicitly in the statusbar:

```python
def _update_statusbar(self) -> None:
    signals = RegressionAnalyzer(self._models).analyze()
    warnings = sum(1 for s in signals if s.severity in ("critical", "warning"))
    # NOTE: grain/upstream signals require a previous snapshot; they are always 0 here.
    self.query_one("#model-list-status", Static).update(
        f"{len(self._models)} models  |  {warnings} row-delta regression warnings"
    )
```

---

### WR-04: UTC Clock Timer Fires on Background (Suspended) Screen

**File:** `terminair/screens/model_list.py:91`

**Issue:** `set_interval(1.0, self._update_header)` is registered in `on_mount`. Because Textual caches the `ModelListScreen` instance in `_installed_screens` after the first push (confirmed by tracing `App.get_screen` → `self._installed_screens[screen] = next_screen`), the screen is never destroyed and its timer never stops. The timer fires every second even when `ModelDetailScreen`, `LineageScreen`, or `ProblemsScreen` is the active screen, calling `query_one` on a suspended screen's widget tree. This is not a crash (the widget is still mounted), but it performs a DOM traversal and a Rich `Text` render for a widget the user cannot see.

**Fix:** Check `self.is_active` before updating, or use `on_screen_resume` / `on_screen_suspend` to start and stop the timer:

```python
def on_screen_resume(self) -> None:
    self._clock_timer = self.set_interval(1.0, self._update_header)

def on_screen_suspend(self) -> None:
    if self._clock_timer:
        self._clock_timer.stop()
        self._clock_timer = None

# Remove set_interval from on_mount
async def on_mount(self) -> None:
    self._clock_timer = None
    await self._load_models()
```

---

## Info

### IN-01: Import Inside Hot-Path Method

**File:** `terminair/screens/model_list.py:155-156`

**Issue:** `from datetime import datetime, timezone` is placed inside `_update_header()`, which is called every second by the timer. Python's import machinery caches modules in `sys.modules` so there is no measurable overhead, but the convention is clear: imports belong at the top of the module. Any linter (`ruff`, `isort`) will flag this.

**Fix:** Move the import to the top of `model_list.py` alongside the other imports:

```python
from datetime import datetime, timezone
```

---

### IN-02: _filtered_models() Called Twice Per Render

**File:** `terminair/screens/model_list.py:111,138`

**Issue:** `_render()` computes `visible_models = self._filtered_models()` (line 111) and then `_update_meta()` independently calls `self._filtered_models()` again (line 138). Both calls iterate `self._models` and apply the same filter query, doing double work on every render.

**Fix:** Pass the already-computed list into `_update_meta`:

```python
def _update_meta(self, visible: list[ModelState]) -> None:
    total = len(self._models)
    meta = self.query_one("#model-list-meta", Static)
    meta.update(f"{len(visible)} visible of {total} models  |  filter: {self._filter_query or 'none'}")

# In _render():
visible_models = self._filtered_models()
# ...
self._update_meta(visible_models)
```

---

### IN-03: action_noop Has Explicit `return None`

**File:** `terminair/screens/detail.py:153-154`

**Issue:** `action_noop` explicitly returns `None` from a `-> None` function. This is redundant and unusual in the codebase.

**Fix:**

```python
def action_noop(self) -> None:
    pass
```

---

_Reviewed: 2026-05-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
