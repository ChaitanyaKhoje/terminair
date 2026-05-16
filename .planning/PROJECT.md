# Terminair — dbt Model Intelligence TUI

## What This Is

Terminair is a read-only local developer TUI for answering operational and structural questions about dbt models. It correlates three things the developer already has: a cloned dbt repo (manifest.json + run_results.json), a cloned Airflow app repo (DAG definitions), and an optional live Airflow stack. The manifest.json is the primary source of truth; Airflow and Snowflake are narrow enrichment sources.

**v1.0 shipped:** 4 screens (ModelList, Problems, Lineage, ModelDetail), full dbt data layer with 6 regression signal types, demo mode requiring zero external services, 117 tests.

## Core Value

A developer working on dbt models can instantly see what is happening with any model, why it is a problem, and what its full lineage looks like — without leaving the terminal and without touching production data.

## Requirements

### Validated (v1.0)

- ✓ Textual-based TUI framework — existing
- ✓ k9s interaction model (key hints visible, filter bar, push/pop screen stack) — existing
- ✓ FlashBar error/warn widget (auto-clears after 8s) — existing
- ✓ CommandPalette — existing
- ✓ Config loading with YAML + env var expansion — existing
- ✓ Read-only enforcement (test suite verifies no write methods) — v1.0
- ✓ dbt data layer (ManifestLoader, ArtifactReader, AirflowBridge, StateAggregator, RegressionAnalyzer, MockDataProvider) — v1.0
- ✓ Fixture files (manifest.json, run_results.json, run_results_previous.json, manifest_previous.json, query_history.json) — v1.0
- ✓ ModelListScreen — live operational dashboard across all dbt models — v1.0
- ✓ ProblemsScreen — failures (self-caused vs upstream-caused) + regression signals — v1.0
- ✓ LineageScreen — ASCII tree (model mode + tag/group mode, 4-hop depth) — v1.0
- ✓ ModelDetailScreen — 5-tab deep-dive (Status, Structure, Variables+Refs, SQL, Regression) — v1.0
- ✓ Config schema: DbtConfig + SnowflakeConfig Pydantic models — v1.0
- ✓ CLI flags: --manifest, --run-results, --dag (repeatable), --demo — v1.0
- ✓ Makefile targets: dbt-demo, dbt-dev — v1.0
- ✓ Test suite: test_manifest.py, test_regression.py, test_aggregator.py, test_mock_data.py — v1.0
- ✓ Removed all deprecated Airflow screens — v1.0
- ✓ grain_added, grain_removed, upstream_schema_change signals visible in TUI (previous-snapshot threading) — v1.0 (Phase 5.1)

### Active (v1.1+)

- [ ] Cold-start UX: hint toward --demo when no config file present (TD-03)
- [ ] Human UAT sign-off on live TUI smoke (deferred from autonomous execution)
- [ ] Dockerfile tested end-to-end with $AIRFLOW_URL env var in a real container

### Out of Scope

- Write actions of any kind — read-only is a hard constraint, enforced by test suite
- dbt run triggering — not a CI tool
- Airflow task clears or retries — Airflow is a data source only
- DAG list as primary view — replaced by ModelListScreen
- Pools, health, SLA misses, resource timeline, XCom screens — k9s already covers these
- Log streaming — out of scope for v1
- dbt Cloud API — local artifacts only
- Charts or sparklines — row counts are numeric text only
- dbt docs integration — not planned
- Schema evolution tracking beyond grain diff — deferred

## Context

**Shipped v1.0 with 5,588 LOC Python** across the dbt data layer, 4 screens, config/CLI extension, and test suite. Tech stack: Python 3.11+, Textual ≥0.80, Pydantic v2, Click, PyYAML, Rich.

**Architecture pattern established:** StateAggregator and MockDataProvider share identical async interfaces (`get_models()`, `get_previous_models()`). Screens call `_load_models()` which fetches both current and previous snapshots — previous snapshot enables all 6 regression signal types. The `--demo` flag selects MockDataProvider with pre-seeded grain drift for demo-visible signals.

**Known tech debt at v1.0 close:** Cold-start error message has no `--demo` hint; REQUIREMENTS.md CLN-02/03 checkboxes were stale (fixed in archive). Human UAT deferred.

## Constraints

- **Tech stack**: Python 3.11+, Textual ≥0.80, Pydantic v2, Click, PyYAML, Rich — no new major dependencies unless strictly necessary
- **Read-only**: AirflowBridge and SnowflakeClient must have zero write methods — enforced by test_read_only.py with inspect + AST scan
- **Local artifacts only**: manifest.json and run_results.json consumed from local filesystem; no dbt Cloud API
- **No prod data**: Local Airflow demo stack + fixture files are the only data sources during development
- **Snowflake optional**: Entire snowflake config block is optional; absence must not crash anything

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| dbt artifacts-first architecture | manifest.json is source of truth; Airflow and Snowflake are narrow enrichment sources | ✓ Good — screens are data-shape stable |
| Remove Airflow screens entirely (not stub/archive) | Clean break — Airflow observability is k9s's job | ✓ Good — clean codebase from day 1 |
| AirflowBridge replaces AirflowClient | Narrow interface (GET only, status + pod_name) prevents scope creep | ✓ Good — read-only enforced by test |
| StateAggregator as single composition root | Screens never call data sources directly — testability | ✓ Good — mock swap trivial |
| MockDataProvider as drop-in for StateAggregator | All 4 screens testable with no external services | ✓ Good — demo mode works |
| Horizontal layers build order | dbt data layer first, then screens — reduces data shape risk | ✓ Good — phases 1-2 found and fixed all data shape issues before UI work |
| Separate get_previous_models() method (not tuple return) | Zero churn to DbtScreen base class; screens opt in per override | ✓ Good — LineageScreen unaffected |
| Timer in on_screen_resume (not on_mount) for clock | Avoid firing on suspended background screen | ⚠ Revisit — bug: clock never fired on initial mount; fixed by also calling _update_header() in on_mount |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-16 after v1.0 milestone*
