# Terminair — Project Retrospective

## Milestone: v1.0 — dbt Model Intelligence TUI

**Shipped:** 2026-05-16
**Phases:** 6 (5 planned + 1 inserted) | **Plans:** 12 | **Tests:** 117

### What Was Built

- Full Airflow TUI layer removed (26 files, 1065-line app.py reduced to ~170 lines)
- dbt data layer: ManifestLoader, ArtifactReader, AirflowBridge, StateAggregator, RegressionAnalyzer, MockDataProvider with all 6 signal types
- 5 fixture files (manifest.json, run_results.json x2, manifest_previous.json, query_history.json)
- Config extension: DbtConfig + SnowflakeConfig Pydantic models, --demo/--manifest/--run-results/--dag CLI flags
- 4 screens: ModelList (tag filter, clock, statusbar), Problems (severity-colored signals), Lineage (ASCII tree, 4-hop depth), ModelDetail (5 tabs, scrollable SQL, 1-5 key nav)
- Full test suite: 117 tests across test_manifest.py, test_regression.py, test_aggregator.py, test_mock_data.py, test_read_only.py (inspect+AST)
- Dockerfile + Makefile targets (dbt-demo, dbt-dev)
- Phase 5.1 (inserted): threaded previous-snapshot to all screens so grain_added/grain_removed/upstream_schema_change signals reach the TUI

### What Worked

- **Horizontal layers approach (Approach B):** Building and testing the dbt data layer completely before writing any screens caught data shape issues early and made screen development fast — every screen "just worked" against the real data contract.
- **MockDataProvider as drop-in:** The identical interface between StateAggregator and MockDataProvider meant `--demo` mode was testable from day 1. All 4 screens verified without any external services.
- **Audit-driven gap fill:** Phases 3, 4, and 5 were mostly pre-implemented. The GSD research phase reliably detected this and planned surgical gap-fill rather than reimplementation. This saved significant work.
- **Code review automation:** The review/fix cycle caught real bugs every phase (Dockerfile AIRFLOW_URL default, cursor_row read-only property, grain signal threading). None were caught by the test suite alone.

### What Was Inefficient

- **Autonomous mode deferred human UAT:** Phases 4 and 5 have `human_needed` verification that was auto-approved without actually running `make dbt-demo`. The deferred UAT creates debt at milestone close.
- **Test file naming:**  Phase 2 wrote `test_regression_and_mock.py` combining two concerns; Phase 5 had to split it. Upfront naming discipline would have avoided the split work.
- **plan-checker repeated pattern:** Every plan had the same two non-blocking warnings (Open Questions lacks RESOLVED suffix; empty `<files>` on verify tasks). These are documentation hygiene issues that required fixing each time. Could be made skippable for known patterns.
- **Integration checker found grain signal gap at milestone audit** that should have been caught at Phase 4 verification. The verifier only checks what tests cover; the integration checker reasons about untested paths.

### Patterns Established

- `async def get_previous_models() -> list[ModelState]` — standard provider interface for snapshot comparison
- Dual-channel warnings: `_logger.warning` + `self._flash_warn()` for any degraded-data condition
- Timer in `on_screen_resume`/`on_screen_suspend` (not `on_mount`) for live TUI timers — but call once directly in `on_mount` for immediate first render
- `_previous_models or None` pattern — converts empty list to None for RegressionAnalyzer to distinguish "no previous configured" from "previous is empty list"
- `inspect.getmembers + AST scan` for read-only enforcement — catches HTTP verb calls inside method bodies, not just method names

### Key Lessons

1. **Research phase is cheap, execution is expensive.** The researcher reliably detected pre-implemented code in phases 3-5 and redirected to gap-fill. Always let research run even for "obvious" phases.
2. **Code review catches what tests miss.** The DB cursor_row read-only bug, the Dockerfile demo-branch unreachability, and the grain signal threading gap were all caught by the review agent, not by tests.
3. **Integration checker at milestone audit is essential.** It reasons about cross-phase wiring that no individual phase verifier can see. Run it before claiming milestone complete.
4. **Plan checker warnings accumulate.** The same two documentation warnings (RESOLVED marker, empty files tag) appeared in every phase. Build a suppression list or fix them upstream.

### Cost Observations

- Sessions: ~4 (initial setup + phases 1-2, phases 3-4, phase 5 + audit, milestone complete)
- Model: claude-sonnet-4-6 throughout
- Notable: Autonomous mode (`/gsd-autonomous --from 3`) executed phases 3-5 + 5.1 in a single session with minimal interruption

---

## Cross-Milestone Trends

*(To be populated after v1.1)*
