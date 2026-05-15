# Phase 4: Screens - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — all 4 screens pre-implemented during Phase 2 development)

<domain>
## Phase Boundary

All four dbt screens (ModelListScreen, ProblemsScreen, LineageScreen, ModelDetailScreen) already exist in `terminair/screens/` and are wired in `app.py`. This phase is an audit-and-gap-fill: verify each screen meets the ROADMAP success criteria and close any gaps found.

Files that exist:
- `terminair/screens/model_list.py` — ModelListScreen (156 lines)
- `terminair/screens/problems.py` — ProblemsScreen (165 lines)
- `terminair/screens/lineage.py` — LineageScreen (183 lines)
- `terminair/screens/detail.py` — ModelDetailScreen (143 lines)
- `terminair/screens/base.py` — DbtScreen base class (119 lines)

All 4 screens registered in `app.py` SCREENS dict. Bindings: 1→model_list, 2→problems, 3→lineage. ModelDetailScreen accessible via Enter from any screen.

</domain>

<decisions>
## Implementation Decisions

### Known Implementations (verified against ROADMAP success criteria)
- ModelListScreen: has `t` binding for `action_cycle_tag_filter`, FilterInput for `/`, DataTable with model data
- ProblemsScreen: has two-section layout (failures + regression signals)
- LineageScreen: has `m`/`g` mode switching, `+`/`-` depth expansion, ASCII tree rendering
- ModelDetailScreen: has 5 TabbedContent panes (Status, Structure, Variables+Refs, SQL, Regression)
- All screens inherit DbtScreen bindings (/, Esc, r, :, q)

### Gaps to Investigate
- ModelListScreen DataTable columns: ROADMAP requires status/model/tag/status_text/duration/rows/row_delta/dag_id — verify all 8 columns present
- ProblemsScreen upstream-caused vs self-caused distinction: verify `has_upstream_failure` field drives visual separation
- LineageScreen depth expansion behavior: verify +/- actually changes `_depth` and re-renders
- ModelDetailScreen Enter-from-any-screen navigation: verify push_screen plumbing works from all 3 list screens
- Esc from detail screen: verify returns to previous screen without losing navigation position

### Claude's Discretion
- If minor gaps found (missing column, weak Esc handling), fix inline during planning/execution
- If a screen has significant missing functionality, create a targeted plan for it

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `terminair/screens/base.py` DbtScreen — base class with shared bindings (/, Esc, r, :, q) and FlashBar integration
- `terminair/widgets/filter_input.py` — FilterInput widget used by ModelListScreen
- `terminair/dbt/models.py` — ModelState dataclass (source of truth for data shape)
- `terminair/dbt/mock_data.py` — MockDataProvider for testing screens without live data
- `terminair/app.py` — _switch_to() and push_screen() routing already wired

### Established Patterns
- Screens use `SCROLLABLE = False`, compose with DataTable + border-title + optional FilterInput + footer Static
- Data loading: `asyncio.create_task(self._load_*())` in `on_mount` or after navigation
- Error feedback: `self._flash_error(f"context: {str(e)[:80]}")` in except blocks
- Screen switching: `self._switch_to(screen_name)` for number keys, `push_screen()` for drill-in

### Integration Points
- StateAggregator / MockDataProvider → screens via `app.get_data_provider()`
- All screens wired in app.py SCREENS dict and BINDINGS

</code_context>

<specifics>
## Specific Ideas

- If DataTable columns in ModelListScreen are incomplete, add missing columns following the existing `add_column` pattern in the screen
- ModelDetailScreen is in `terminair/screens/detail.py` (ModelDetailScreen) with a compatibility shim at `terminair/screens/model_detail.py`
- The `terminair/screens/__init__.py` exports all screen classes

</specifics>

<deferred>
## Deferred Ideas

- Full test coverage for screens (deferred to Phase 5)
- `make dbt-demo` Makefile target (deferred to Phase 5)
- Dockerfile (deferred to Phase 5)

</deferred>
