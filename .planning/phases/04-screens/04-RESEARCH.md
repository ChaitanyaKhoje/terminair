# Phase 4: Screens - Research

**Researched:** 2026-05-15
**Domain:** Textual TUI screen audit — gap-fill against ROADMAP success criteria
**Confidence:** HIGH (all findings verified directly from source code and Textual runtime)

## Summary

All four dbt screens (ModelListScreen, ProblemsScreen, LineageScreen, ModelDetailScreen) exist in `terminair/screens/` and are registered in `app.py`. The shared `DbtScreen` base class provides /, Esc, r, :, q bindings for SCR-05. The majority of each screen's success criteria are already met.

Three concrete gaps remain before requirements SCR-01, SCR-03, and SCR-04 are satisfied:
1. ModelListScreen (SCR-01) is missing a topbar connection+clock field and a bottom statusbar showing regression warning count.
2. LineageScreen (SCR-03) initializes `_depth = 3` but the ROADMAP success criterion states "4-hop depth default."
3. ModelDetailScreen (SCR-04) has no 1-5 key bindings for tab switching, and the SQL tab uses a non-scrollable `Static` widget — the ROADMAP requires "full compiled SQL scrollable."

SCR-02 (ProblemsScreen) and SCR-05 (shared bindings + Esc navigation) are fully implemented and require no changes.

**Primary recommendation:** Three targeted fix tasks — one per gap cluster. Execute in sequence: ModelListScreen statusbar → LineageScreen depth default → ModelDetailScreen tab keys + SQL scrollability.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All four dbt screens pre-exist; this phase is audit-and-gap-fill only.
- ModelListScreen: has `t` binding for `action_cycle_tag_filter`, FilterInput for `/`, DataTable with model data — verified present.
- ProblemsScreen: has two-section layout (failures + regression signals) — verified present.
- LineageScreen: has `m`/`g` mode switching, `+`/`-` depth expansion, ASCII tree rendering — verified present.
- ModelDetailScreen: has 5 TabbedContent panes (Status, Structure, Variables+Refs, SQL, Regression) — verified present.
- All screens inherit DbtScreen bindings (/, Esc, r, :, q) — verified present.
- StateAggregator / MockDataProvider → screens via `app.get_data_provider()` — wired in app.py.

### Claude's Discretion
- If minor gaps found (missing column, weak Esc handling), fix inline during planning/execution.
- If a screen has significant missing functionality, create a targeted plan for it.

### Deferred Ideas (OUT OF SCOPE)
- Full test coverage for screens (deferred to Phase 5).
- `make dbt-demo` Makefile target (deferred to Phase 5).
- Dockerfile (deferred to Phase 5).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCR-01 | ModelListScreen (key 1) — topbar with connection + clock, tag filter tabs cycled with t, text filter with /, DataTable with status/model/tag/status_text/duration/rows/row_delta/dag_id columns, bottom statusbar with counts and regression warning count | GAPS: topbar connection+clock missing; statusbar with regression warning count missing. All other elements verified present. |
| SCR-02 | ProblemsScreen (key 2) — two stacked sections with upstream-caused vs self-caused distinction and severity-colored regression signals; Enter → ModelDetailScreen | FULLY MET: failure-table has `cause` column (upstream=yellow, self=red); signal-table has severity_style map; Enter routes via `_open_detail`. |
| SCR-03 | LineageScreen (key 3) — ASCII tree model mode (4-hop depth default, +/- expand/collapse) and tag/group mode; toggled with m/g; Rich markup for status colors | GAP: `_depth` initialized to 3, not 4. All other elements present. |
| SCR-04 | ModelDetailScreen (Enter from any screen) — 5 tabs navigated with 1-5 or arrow keys; full compiled SQL scrollable; no modal overlays | GAPS: no 1-5 key bindings for tab navigation; SQL tab uses non-scrollable `Static`. Arrow-key navigation is present via Textual's Tabs BINDINGS (left/right built-in). |
| SCR-05 | All screens share consistent filter (/ to open, Esc to clear), Esc to back, r to refresh, : for command palette, q to quit | FULLY MET: DbtScreen.BINDINGS covers all; action_back() → app.action_back() → pop_screen() if len>2. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DataTable rendering | Screen (Textual widget) | — | Screens own their own UI composition |
| Data loading / provider access | Screen (via app.get_data_provider()) | App (lazy init) | Screen triggers load; app owns provider |
| Navigation routing | App (_switch_to, push_screen) | Screen (action_back delegates to app) | App owns screen stack |
| Filter state | Screen (_filter_query) | FilterInput widget | Each screen owns its own filter state |
| Selected model state | App (selected_model_id) + Screen (_selected_model_id) | — | Shared for cross-screen drill-in |
| Tab switching (detail) | Screen (ModelDetailScreen BINDINGS + TabbedContent.active) | — | Screen owns its own tab state |
| Error feedback | App (FlashBar) | Screen (delegates via app_typed._flash_error) | FlashBar is a top-level app widget |

## Gap Analysis (Verified Against Source)

### SCR-01: ModelListScreen — Two Gaps

**Gap 1 — Topbar connection + clock:**
The `compose()` method yields `Static("dbt models", id="model-list-header")` as the only header. There is no connection URL display and no clock. The `app.get_config()` method is available from `DbtScreen.app_typed`; connection URL can be read from `self.app_typed.get_config()`. A live clock would require a `set_interval` callback.
[VERIFIED: terminair/screens/model_list.py lines 74-75]

**Gap 2 — Bottom statusbar with regression warning count:**
`_update_meta()` writes to `#model-list-meta` (second line in header area): `"{visible} visible of {total} models  |  filter: {filter}"`. There is no bottom statusbar at all, and no regression warning count anywhere. The `RegressionAnalyzer` is already imported in `problems.py` — it can be reused in ModelListScreen to compute the count.
[VERIFIED: terminair/screens/model_list.py lines 124-128]

**All 8 DataTable columns present:**
`_render()` calls `add_column` for: status, model, tag, status_text, duration, rows, row_delta, dag_id. All 8 columns specified by SCR-01 are present.
[VERIFIED: terminair/screens/model_list.py lines 92-99]

### SCR-02: ProblemsScreen — FULLY MET

- Two-section layout: `#failure-table` and `#signal-table` separated by heading Statics.
- Upstream-caused vs self-caused: `cause = "upstream" if model.has_upstream_failure else "self"` — `upstream` renders yellow, `self` renders red.
- Severity coloring: `severity_style` dict maps critical→bold red, warning→bold yellow, info→dim.
- Enter → ModelDetailScreen: `on_data_table_row_selected` calls `_open_detail(node_id)` for both tables.
[VERIFIED: terminair/screens/problems.py lines 97-140]

### SCR-03: LineageScreen — One Gap

**Gap — Default depth is 3, not 4:**
`self._depth = 3` in `__init__`. The ROADMAP success criterion states "4-hop depth default." The `visit()` function returns early when `depth >= self._depth`, so `_depth=3` shows root + 3 child levels (hops 0-3). Setting `_depth=4` shows root + 4 child levels per the spec.
[VERIFIED: terminair/screens/lineage.py line 55]

All other SCR-03 elements verified present: m/g mode switching, +/- depth actions, ASCII tree with branch characters (├─, └─), status color markup.
[VERIFIED: terminair/screens/lineage.py lines 44-48, 97-131, 159-172]

### SCR-04: ModelDetailScreen — Two Gaps

**Gap 1 — No 1-5 key bindings for tab navigation:**
`ModelDetailScreen.BINDINGS = DbtScreen.BINDINGS + [Binding("enter", "noop", "Open")]`. No 1-5 number key bindings exist. The ROADMAP specifies "navigated with 1-5 or arrow keys."

Arrow keys ARE present via Textual's built-in `Tabs.BINDINGS = [('left', 'previous_tab'), ('right', 'next_tab')]` — verified at runtime.
[VERIFIED: terminair/screens/detail.py lines 49-51; runtime: `Tabs.BINDINGS` inspection]

1-5 key bindings must be added to `ModelDetailScreen.BINDINGS` with actions that set `TabbedContent.active`. The TabPanes have no explicit `id` attributes, so Textual auto-assigns `tab-1` through `tab-5`.

**Important:** App.BINDINGS has `Binding("1")` through `Binding("4")` for screen switching. When ModelDetailScreen is active, screen-level bindings take priority over app-level bindings (Textual's binding priority chain: focused_widget → screen → app). Adding 1-5 bindings to ModelDetailScreen will correctly shadow the app's 1-4 screen-switching bindings while on the detail screen.
[VERIFIED: Textual binding priority model — Context7 docs and runtime inspection]

**Gap 2 — SQL tab is not scrollable:**
`TabPane("SQL", Static("", id="detail-sql", classes="detail-pane"))` — `Static` is not focusable and has no scroll support. Long compiled SQL will be clipped. The ROADMAP requires "full compiled SQL scrollable."

Fix: Wrap `Static` in `VerticalScroll` container, or replace with `TextArea(read_only=True)`. `VerticalScroll` is the simpler option matching the existing codebase pattern (no new imports needed).
[VERIFIED: `Static.can_focus = False`; `VerticalScroll` available in `textual.containers`]

### SCR-05: All Screens — FULLY MET

DbtScreen.BINDINGS includes: ctrl+c (quit, priority), q (quit), escape (back), r (refresh), / (focus_filter), : (command_palette). All 4 screens inherit this via `DbtScreen.BINDINGS + [...]`.

Esc navigation behavior verified:
- `action_back()` in DbtScreen delegates to `app.action_back()`.
- `app.action_back()` calls `pop_screen()` only when `len(self.screen_stack) > 2`.
- Floor is `[DefaultScreen, model_list]` (len=2); detail screen at len=3 pops cleanly.
- Navigation position is preserved: Textual screens in the SCREENS dict are instantiated once and not re-mounted on pop. The DataTable cursor state remains.
[VERIFIED: terminair/app.py lines 240-242; terminair/screens/base.py lines 66-67]

## Standard Stack

### Core (All Verified Installed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| textual | 8.2.6 | TUI framework | [VERIFIED: runtime `textual.__version__`] |
| rich | (textual dep) | Text markup, Text objects | Used in all screens for styled output |
| python | 3.11+ | Runtime | [VERIFIED: uv.lock] |

### Key Textual APIs Used in This Phase

| API | Source | Notes |
|-----|--------|-------|
| `TabbedContent.active = "tab-N"` | Textual docs | Sets active tab by id string |
| `TabPane(title, id="tab-N")` | Textual docs | Auto-assigned as tab-1..tab-5 if no id set |
| `Tabs.BINDINGS` left/right | Runtime verified | Built-in tab navigation; no code needed |
| `VerticalScroll` container | textual.containers | Wraps any widget with scroll support |
| `app.get_config()` | terminair/app.py | Returns Config with connection URL |
| `set_interval(seconds, callback)` | Textual App | For live clock in ModelListScreen header |
| `RegressionAnalyzer(models).analyze()` | terminair/dbt/regression.py | Produces regression signals for count |

## Architecture Patterns

### System Architecture Diagram

```
User keypress
     │
     ▼
DbtScreen BINDINGS (/, Esc, r, :, q)
     │
     ├─ / → FilterInput.open() → _on_filter_change() → _render()
     ├─ Esc → app.action_back() → pop_screen() [if len>2]
     ├─ r → _queue_reload() → run_worker(_load_models())
     └─ 1-5 (detail only) → TabbedContent.active = "tab-N"
          │
     ▼
app.get_data_provider()
     │
     ├─ MockDataProvider (demo mode / missing manifest)
     └─ StateAggregator (manifest + run_results + optional bridge/snowflake)
          │
          ▼
     list[ModelState]
          │
          ├─ ModelListScreen._render() → DataTable (8 cols)
          ├─ ProblemsScreen._render() → failure-table + signal-table
          ├─ LineageScreen._render() → lineage-table (ASCII tree or group list)
          └─ ModelDetailScreen._render() → 5 TabPanes
```

### Recommended Fix Structure

No new files needed. All fixes are targeted edits to existing screen files.

```
terminair/screens/
├── model_list.py   — Add connection+clock to header; add bottom statusbar with regression count
├── lineage.py      — Change self._depth = 3 → self._depth = 4
└── detail.py       — Add 1-5 BINDINGS + action_switch_tab(); wrap SQL Static in VerticalScroll
```

### Pattern: Tab Switching by Number Key

```python
# Source: Textual docs + runtime verification
# In ModelDetailScreen:
BINDINGS = DbtScreen.BINDINGS + [
    Binding("enter", "noop", "Open"),
    Binding("1", "switch_tab('tab-1')", "Status", show=False),
    Binding("2", "switch_tab('tab-2')", "Structure", show=False),
    Binding("3", "switch_tab('tab-3')", "Refs", show=False),
    Binding("4", "switch_tab('tab-4')", "SQL", show=False),
    Binding("5", "switch_tab('tab-5')", "Regression", show=False),
]

def action_switch_tab(self, tab_id: str) -> None:
    self.query_one("#detail-tabs", TabbedContent).active = tab_id
```

Note: `show=False` prevents these from cluttering the footer since there are already many bindings.

### Pattern: Scrollable SQL Pane

```python
# Source: Textual docs (VerticalScroll is the standard scrollable container)
from textual.containers import VerticalScroll

# In compose():
with TabPane("SQL"):
    with VerticalScroll():
        yield Static("", id="detail-sql", classes="detail-pane")
```

### Pattern: Regression Count in ModelListScreen

```python
# Reuse RegressionAnalyzer already imported in problems.py
from terminair.dbt.regression import RegressionAnalyzer

def _update_statusbar(self) -> None:
    signals = RegressionAnalyzer(self._models).analyze()
    warnings = sum(1 for s in signals if s.severity in ("critical", "warning"))
    # Update bottom statusbar Static
    self.query_one("#model-list-status", Static).update(
        f"{len(self._models)} models  |  {warnings} regression warnings"
    )
```

### Pattern: Connection + Clock in Header

```python
# app.get_config() returns Config; connection URL from default connection
def _update_header(self) -> None:
    config = self.app_typed.get_config()
    conn = config.connections.get(config.settings.default_connection)
    url = conn.url if conn else "demo"
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    self.query_one("#model-list-header", Static).update(f"dbt models  |  {url}  |  {ts}")
```

Clock refresh: call `_update_header()` from within `_render()` (called on every data load and filter change). For a live ticking clock independent of data, add `self.set_interval(1.0, self._update_header)` in `on_mount`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scrollable SQL view | Custom scroll logic | `VerticalScroll` container | Textual built-in; handles terminal resize |
| Tab keyboard nav left/right | Custom key handling | Textual's `Tabs.BINDINGS` (built-in) | Already present via TabbedContent → Tabs |
| Tab active state | Custom state tracker | `TabbedContent.active` reactive | Textual handles rendering |
| Regression signal count | Separate aggregation | `RegressionAnalyzer(self._models).analyze()` | Already exists in dbt/regression.py |

## Common Pitfalls

### Pitfall 1: TabPane Auto-ID Assumption
**What goes wrong:** Assuming `tab-1` through `tab-5` without verifying — if TabPane has any `id` attribute set, the auto-assigned IDs change.
**Why it happens:** Textual assigns `tab-1`, `tab-2`, etc. only for TabPanes without explicit `id`.
**How to avoid:** Either add explicit IDs (`id="tab-status"` etc.) and reference those, or verify auto-assignment. Current code has NO `id` on TabPanes → auto-assigned `tab-1` through `tab-5`.
**Warning signs:** Tab switching selects wrong pane or throws `NoMatches`.

### Pitfall 2: Number Key Binding Shadowing
**What goes wrong:** Adding 1-5 to ModelDetailScreen makes keys 1-4 no longer navigate between screens when on the detail screen.
**Why it happens:** Screen-level bindings shadow app-level bindings.
**How to avoid:** This is the CORRECT and desired behavior per SCR-04. When on detail, 1-5 = tab nav. When on list screens, 1-3 = screen nav. Document this intentional shadowing.
**Warning signs:** Calling it a bug — it is not.

### Pitfall 3: Static Widget Not Scrollable
**What goes wrong:** Long compiled SQL gets clipped at the bottom of the SQL tab with no way to scroll.
**Why it happens:** `Static` is a simple text rendering widget with `can_focus=False` and no overflow behavior.
**How to avoid:** Wrap `Static` in `VerticalScroll`. Alternatively use `TextArea(read_only=True)` for syntax-aware display, but that adds complexity.
**Warning signs:** SQL over ~50 lines is cut off; user cannot reach the end.

### Pitfall 4: set_interval for Clock Causes Excessive Re-renders
**What goes wrong:** A 1-second clock tick calls `_update_header()` which calls `Static.update()` — fine in isolation, but if it triggers a full `_render()`, it reloads data every second.
**Why it happens:** Conflating the header update function with the full render.
**How to avoid:** `_update_header()` should ONLY update the header Static, NOT call `_render()` or `_load_models()`. Keep the clock update path separate from the data load path.
**Warning signs:** CPU spikes; API calls happening every second.

### Pitfall 5: VerticalScroll Breaks TabPane Layout
**What goes wrong:** Wrapping Static in VerticalScroll without setting height causes the scroll container to collapse to zero height.
**Why it happens:** VerticalScroll needs explicit height or `height: 1fr` in CSS to expand.
**How to avoid:** Add CSS `#detail-sql-scroll { height: 1fr; }` or set `height="1fr"` on the VerticalScroll widget. The `detail-pane` class currently sets `padding: 1 1` only.
**Warning signs:** SQL tab appears empty; VerticalScroll renders at 0px height.

## Code Examples

### Switch Active Tab
```python
# Source: https://github.com/textualize/textual/blob/main/docs/widgets/tabbed_content.md
self.query_one(TabbedContent).active = "tab-2"
# Auto-assigned IDs: tab-1 (Status) through tab-5 (Regression)
```

### VerticalScroll Wrapping Static
```python
# Source: https://context7.com/textualize/textual/llms.txt (containers)
from textual.containers import VerticalScroll
from textual.widgets import Static

with TabPane("SQL"):
    with VerticalScroll(id="detail-sql-scroll"):
        yield Static("", id="detail-sql", classes="detail-pane")
```

### RegressionAnalyzer Count
```python
# Source: terminair/dbt/regression.py (verified existing API)
from terminair.dbt.regression import RegressionAnalyzer
signals = RegressionAnalyzer(self._models).analyze()
warning_count = sum(1 for s in signals if s.severity in ("critical", "warning"))
```

## State of the Art

| Area | Current | Correct per Spec | Fix |
|------|---------|-----------------|-----|
| LineageScreen depth default | `_depth = 3` | 4-hop | `_depth = 4` in `__init__` |
| ModelDetailScreen tab keys | None (only left/right built-in) | 1-5 + left/right | Add BINDINGS + action_switch_tab() |
| SQL tab scrollability | `Static` (not scrollable) | Scrollable | Wrap in `VerticalScroll` |
| ModelListScreen topbar | "dbt models" only | connection + clock | Update _update_header / set_interval |
| ModelListScreen statusbar | None | counts + regression warning count | Add Static + _update_statusbar() |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TabPanes without explicit `id` get auto-assigned `tab-1` through `tab-5` sequentially | Code Examples | If Textual changes this, switching to `tab-N` breaks silently; mitigate by adding explicit ids |

All other claims in this research were verified directly from source code or Textual runtime.

## Open Questions (RESOLVED)

1. **Clock update frequency**
   - What we know: `set_interval(1.0, callback)` works in Textual; calling it in `on_mount` is safe.
   - What's unclear: Whether the user expects a live-ticking clock or just a "last refreshed" timestamp.
   - Recommendation: Implement as a 1-second interval updating only the header Static. If it causes performance concern, increase interval to 30s.
   - RESOLVED: 1-second interval via `set_interval(1.0, self._update_header)` in `on_mount`. Clock is isolated from data reload path.

2. **Regression count scope in ModelListScreen**
   - What we know: `RegressionAnalyzer(self._models).analyze()` computes all signals.
   - What's unclear: Whether the count should be total signals or only critical+warning.
   - Recommendation: Show critical+warning count only (info signals are low-signal noise), labeled "N warnings."
   - RESOLVED: Show critical+warning count only — `sum(1 for s in signals if s.severity in ("critical", "warning"))`, labeled as regression warnings.

## Environment Availability

Step 2.6: SKIPPED — phase is pure code edits to existing Python files; no external tool dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv run pytest) |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest terminair/tests/ -x -q` |
| Full suite command | `uv run pytest terminair/tests/ -v` |

### Current Test Suite
- 112 tests passing (verified by running suite).
- No existing screen-specific UI tests (those are Phase 5 scope per CONTEXT.md).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCR-01 | ModelListScreen has 8 columns | Manual smoke | `uv run python3 -m terminair --demo` | N/A — Phase 5 |
| SCR-01 | Regression warning count in statusbar | Manual smoke | `uv run python3 -m terminair --demo` | N/A — Phase 5 |
| SCR-03 | Lineage default depth=4 | Unit (instantiation) | `uv run pytest terminair/tests/ -x -q` | ❌ Phase 5 |
| SCR-04 | 1-5 tab key switching | Manual smoke | `uv run python3 -m terminair --demo` | N/A — Phase 5 |
| SCR-04 | SQL pane scrollable | Manual smoke | `uv run python3 -m terminair --demo` | N/A — Phase 5 |
| SCR-05 | Esc returns to list | Manual smoke | `uv run python3 -m terminair --demo` | N/A — Phase 5 |

### Sampling Rate
- **Per task commit:** `uv run pytest terminair/tests/ -x -q` (112 tests, 0.16s — ensures no regressions)
- **Per wave merge:** `uv run pytest terminair/tests/ -v`
- **Phase gate:** Full suite green + manual smoke of `--demo` mode before `/gsd-verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers regression prevention. Screen behavioral tests are deferred to Phase 5 per locked CONTEXT.md decision.

## Security Domain

Phase 4 is pure UI rendering — no authentication, session management, access control, input handling (filter input is display-only filter, not executed), or cryptography. No ASVS categories apply.

Security enforcement: SCR-05 is read-only navigation only; no write paths introduced.

## Sources

### Primary (HIGH confidence)
- Direct source code reading: terminair/screens/{base,model_list,problems,lineage,detail}.py — all gap findings
- Direct source code reading: terminair/app.py — BINDINGS, _switch_to, action_back, screen_stack
- Direct source code reading: terminair/dbt/models.py — ModelState fields
- Runtime inspection: `Tabs.BINDINGS` → `[('left', 'previous_tab'), ('right', 'next_tab')]`
- Runtime inspection: `Static.can_focus = False`
- Runtime inspection: textual version 8.2.6
- Runtime test run: `uv run pytest terminair/tests/ -x -q` → 112 passed

### Secondary (MEDIUM confidence)
- Context7 /textualize/textual — TabbedContent.active pattern, VerticalScroll, TabPane auto-IDs [CITED: https://github.com/textualize/textual/blob/main/docs/widgets/tabbed_content.md]

## Metadata

**Confidence breakdown:**
- Gap identification: HIGH — all gaps found via direct source code reading
- Standard Stack: HIGH — Textual 8.2.6 confirmed at runtime
- Architecture: HIGH — verified from existing code patterns
- Pitfalls: HIGH — derived from actual code inspection + Textual API verification

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable Textual APIs; project code is stable)
