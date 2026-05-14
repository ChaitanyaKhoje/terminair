# Terminair — dbt Model Intelligence TUI

## What This Is

Terminair is a read-only local developer TUI for answering operational and structural questions about dbt models. It runs locally, correlating three things the developer already has: a cloned dbt repo (manifest.json + run_results.json), a cloned Airflow app repo (DAG definitions), and a live local Airflow stack (task status + pod names from Kubernetes). Airflow and Snowflake are data sources only — the manifest.json is the primary source of truth.

## Core Value

A developer working on dbt models can instantly see what is happening with any model, why it is a problem, and what its full lineage looks like — without leaving the terminal and without touching production data.

## Requirements

### Validated

- ✓ Textual-based TUI framework — existing
- ✓ k9s interaction model (key hints visible, filter bar, push/pop screen stack) — existing
- ✓ FlashBar error widget (auto-clears after 8s) — existing
- ✓ CommandPalette — existing
- ✓ Config loading with YAML + env var expansion — existing
- ✓ Read-only enforcement (test suite verifies no write methods) — existing

### Active

- [ ] dbt data layer (ManifestLoader, ArtifactReader, AirflowBridge, StateAggregator, RegressionAnalyzer, MockDataProvider)
- [ ] Fixture files (manifest.json, run_results.json, run_results_previous.json, manifest_previous.json, query_history.json)
- [ ] ModelListScreen — live operational dashboard across all dbt models
- [ ] ProblemsScreen — failures (self-caused vs upstream-caused) + regression signals
- [ ] LineageScreen — ASCII tree (model mode + tag/group mode)
- [ ] ModelDetailScreen — 5-tab deep-dive (Status, Structure, Variables+Refs, SQL, Regression)
- [ ] Config schema extended with DbtConfig + SnowflakeConfig Pydantic models
- [ ] CLI flags: --manifest, --run-results, --dag (repeatable), --demo
- [ ] Makefile targets: dbt-demo, dbt-dev
- [ ] Test suite: test_manifest.py, test_regression.py, test_aggregator.py, test_mock_data.py
- [ ] Remove all deprecated Airflow screens (pools, health, SLA misses, resource timeline, XCom, DAG list, etc.)

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

This is a brownfield project — an existing Textual TUI for Apache Airflow is being repositioned as a dbt model intelligence tool. The Airflow TUI layer is being removed entirely; what remains is the Textual framework, theme system, command palette, filter widget, flash widget, and config loading pattern.

**Developer workflow this enables:** Developer has dbt repo cloned locally (provides target/manifest.json, target/run_results.json), Airflow app repo cloned locally (provides DAG definitions), and a local Airflow demo stack running (provides live task status + pod names when on Kubernetes). Terminair correlates all three in one terminal view.

**Airflow task → dbt model mapping:** User passes `--dag` (one or more DAG IDs); terminair lists all tasks for those DAGs from the Airflow REST API and fuzzy-matches task IDs against manifest node names. Pod names come from task instance hostname field.

**Fallback chain:** manifest.json missing → MockDataProvider; Airflow unreachable → status from run_results.json only; Snowflake missing → bytes_scanned=None silently.

**Local testability target:** All 4 screens testable via `make dbt-demo` against MockDataProvider. No external services required for development.

## Constraints

- **Tech stack**: Python 3.11+, Textual ≥0.80, Pydantic v2, Click, PyYAML, Rich — no new major dependencies unless strictly necessary
- **Read-only**: AirflowClient (being replaced by AirflowBridge) and new SnowflakeClient must have zero write methods — enforced by test_read_only.py
- **Local artifacts only**: manifest.json and run_results.json consumed from local filesystem; no dbt Cloud API
- **No prod data**: Local Airflow demo stack + fixture files are the only data sources during development
- **Snowflake optional**: Entire snowflake config block is optional; absence must not crash anything

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| dbt artifacts-first architecture | manifest.json is source of truth; Airflow and Snowflake are narrow enrichment sources | — Pending |
| Remove Airflow screens entirely (not stub/archive) | Clean break — Airflow observability is k9s's job, not terminair's | — Pending |
| AirflowBridge replaces AirflowClient | Narrow interface (GET only, status + pod_name) prevents scope creep back to full Airflow TUI | — Pending |
| StateAggregator as single composition root | Screens never call data sources directly — testability and isolation | — Pending |
| MockDataProvider as drop-in for StateAggregator | All 4 screens testable with no external services via --demo flag | — Pending |
| DAG-name + task scan for Airflow→dbt mapping | User passes --dag IDs; terminair fetches tasks and fuzzy-matches to manifest nodes. No convention required, no dbt model meta changes needed | — Pending |
| Horizontal layers build order | dbt data layer built and tested first, then screens wired incrementally — reduces risk of data shape surprises during UI work | — Pending |
| Approach B: dbt layer first, screens grafted in | Data layer bugs caught before UI work; each milestone independently testable | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-14 after initialization*
