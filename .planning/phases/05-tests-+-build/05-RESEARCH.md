# Phase 5: Tests + Build - Research

**Researched:** 2026-05-15
**Domain:** pytest test organisation, Makefile build targets, Dockerfile entrypoint design
**Confidence:** HIGH

## Summary

Phase 5 is an audit-and-close-gaps phase. The primary implementation work was done in Phases 2–4.
The test suite currently has 112 passing tests across `terminair/tests/` and `terminair/tests/dbt/`.
The Makefile already defines `dbt-demo` and `dbt-dev` targets. The Dockerfile exists, builds
successfully, and produces a working image.

Four concrete gaps remain between what exists and the eight success criteria:

1. **TST-02 / file naming**: Tests for `RegressionAnalyzer` live in `test_regression_and_mock.py`,
   not `test_regression.py`. The 6th signal type (`upstream_schema_change`) has no test in that file.
2. **TST-04 / file naming**: `MockDataProvider` tests live inside `test_regression_and_mock.py`, not
   in a dedicated `test_mock_data.py` file. The tests themselves are comprehensive and all pass.
3. **TST-05 / placeholder**: `tests/test_read_only.py` contains only a `pass` placeholder. The
   success criterion requires it to assert that `AirflowBridge` has zero write methods. The actual
   assertion logic already exists in `tests/dbt/test_airflow_bridge.py` and can be copied.
4. **BLD-03 / Dockerfile wiring**: The `CMD` always launches in `--demo` mode. The Dockerfile
   defines `AIRFLOW_URL=http://localhost:8080` as an env var but the CLI uses `--url` (not an env
   var). To satisfy "connects to a configurable Airflow URL", the CMD must be a shell-form command
   (or entrypoint script) that passes `$AIRFLOW_URL` to the CLI when a URL is set, and falls back
   to `--demo` when it is not.

**Primary recommendation:** All four gaps are small, targeted edits. No structural changes to the
test suite or Makefile are needed. The planner should issue one task per gap.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — all implementation choices are at Claude's discretion.

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase
goal, success criteria, and existing test patterns to guide decisions.

Key gaps to investigate during research:
- Does test_read_only.py actually assert AirflowBridge has zero write methods?
- Do the dbt test files cover all required scenarios (6 signal types, grain precedence, lineage traversal, tick() transitions)?
- Does `make dbt-demo` actually launch the TUI?
- Does the Dockerfile build successfully?

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TST-01 | tests/dbt/test_manifest.py — all ManifestLoader methods against fixtures; grain extraction precedence; var() regex; lineage traversal | SATISFIED — 21 tests, all passing [VERIFIED: live test run] |
| TST-02 | tests/dbt/test_regression.py — all 6 signal types; severity thresholds; sort order (critical first) | PARTIAL — file is named test_regression_and_mock.py; 5 of 6 signal types covered; upstream_schema_change has no test [VERIFIED: grep + test run] |
| TST-03 | tests/dbt/test_aggregator.py — StateAggregator with MockDataProvider injected; has_upstream_failure computation | SATISFIED — file exists, has_upstream_failure tested with skipped upstream and isolated manifest [VERIFIED: live test run] |
| TST-04 | tests/dbt/test_mock_data.py — tick() transitions; row_delta_pct recomputation; all signal types represented | PARTIAL — tests exist and pass in test_regression_and_mock.py, but no standalone test_mock_data.py file exists [VERIFIED: ls + test run] |
| TST-05 | tests/test_read_only.py extended — AirflowBridge has no POST/PUT/DELETE/PATCH methods | GAP — test_read_only.py is a placeholder (pass). Logic exists in test_airflow_bridge.py but requirement specifies test_read_only.py [VERIFIED: file read] |
| BLD-01 | Makefile adds dbt-demo target (runs with --demo flag, no Airflow needed) | SATISFIED — `dbt-demo: setup` → `$(VENV_PYTHON) -m terminair --demo` [VERIFIED: Makefile read] |
| BLD-02 | Makefile adds dbt-dev target (points at local target/ directory via --manifest and --run-results) | SATISFIED — `dbt-dev: setup` → `$(VENV_PYTHON) -m terminair --manifest ./target/manifest.json --run-results ./target/run_results.json` [VERIFIED: Makefile read] |
| BLD-03 | Dockerfile — mounts local target/ directory and connects to a configurable Airflow URL | PARTIAL — Dockerfile builds, VOLUME ["/app/target"] is present, but CMD always uses --demo; AIRFLOW_URL env var is defined but not wired to --url CLI arg [VERIFIED: Dockerfile read + docker build] |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Unit test coverage | Python test layer | — | pytest, no external dependencies |
| Build targets | Makefile | venv setup | All targets are already present |
| Container packaging | Dockerfile | entrypoint shell | Single-binary container is standard |

## Gap Inventory (What Needs to Change)

### Gap 1 — TST-02: Missing test_regression.py + upstream_schema_change test

**Current state:** `terminair/tests/dbt/test_regression_and_mock.py` covers 5 of 6 signal types.
`upstream_schema_change` is implemented in `terminair/dbt/regression.py` (lines 162–188) but has
zero test coverage.

**Required change:**
- Create `terminair/tests/dbt/test_regression.py` containing only `RegressionAnalyzer` tests
  (move the `TestRegressionAnalyzer` class out of `test_regression_and_mock.py`).
- Add a test for `upstream_schema_change`: construct two `ModelState` lists (current/previous) where
  an upstream dep changed its `materialization` or `grain_columns`; assert a `WARNING` signal is
  produced.

**Implementation pattern** (from regression.py lines 165–188):
- `analyze(prev_models)` with upstream dep that has different `materialization` or `grain_columns`
  → expect `signal_type == "upstream_schema_change"` and `severity == Severity.WARNING`.

**Signal type coverage in regression.py** [VERIFIED: source read]:
- `row_drop` — WARNING (<-10%) / CRITICAL (<-30%)
- `row_spike` — WARNING (>50%)
- `grain_added` — WARNING
- `grain_removed` — CRITICAL
- `new_model_no_baseline` — INFO
- `upstream_schema_change` — WARNING (materialization or grain changed on upstream dep)

### Gap 2 — TST-04: Missing test_mock_data.py

**Current state:** `MockDataProvider` tests all exist in `test_regression_and_mock.py` under
`class TestMockDataProvider`. They cover tick() transitions, row_delta_pct recomputation, status
distribution, tag distribution, and copy semantics. All 12 `TestMockDataProvider` tests pass
[VERIFIED: live test run].

**Required change:**
- Create `terminair/tests/dbt/test_mock_data.py` containing only `MockDataProvider` tests.
- Move `TestMockDataProvider` class from `test_regression_and_mock.py` into the new file, OR
  leave tests in place and create a thin `test_mock_data.py` that re-imports and runs them.
- Preferred: move the class cleanly; rename `test_regression_and_mock.py` to `test_regression.py`
  (closing Gap 1 simultaneously).

**Design decision (Claude's discretion):** The cleanest approach is:
1. Create `test_regression.py` with only `TestRegressionAnalyzer` + new `upstream_schema_change` test
2. Create `test_mock_data.py` with only `TestMockDataProvider`
3. Delete `test_regression_and_mock.py` (its content is fully redistributed)

This avoids duplication and satisfies both TST-02 and TST-04 naming requirements.

### Gap 3 — TST-05: test_read_only.py placeholder

**Current state:**
```python
# terminair/tests/test_read_only.py (current)
def test_placeholder_read_only_contract():
    """Placeholder: read-only contract enforcement to be extended in Phase 5."""
    pass
```

**Required change:** Replace the placeholder with an actual assertion that `AirflowBridge` has no
write methods. The logic to copy is in `test_airflow_bridge.py`:

```python
# Source: terminair/tests/dbt/test_airflow_bridge.py lines 31-37 [VERIFIED]
def test_no_write_methods_on_airflow_bridge():
    from terminair.dbt.airflow_bridge import AirflowBridge
    import inspect
    members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
    write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
    assert not write_methods, f"Found write methods: {write_methods}"
```

The `test_airflow_bridge.py` file also has a source-level check (`test_no_write_calls_in_source`).
Add at minimum the `inspect`-based assertion to `test_read_only.py`. Keep the detailed suite in
`test_airflow_bridge.py` (not duplicate).

### Gap 4 — BLD-03: Dockerfile CMD does not wire AIRFLOW_URL

**Current Dockerfile CMD** [VERIFIED: file read]:
```dockerfile
ENV AIRFLOW_URL=http://localhost:8080
CMD ["python", "-m", "terminair", "--demo"]
```

`AIRFLOW_URL` is defined but never passed to the CLI. The CLI uses `--url`, not `AIRFLOW_URL`.

**Required change:** Change CMD to shell form so it can conditionally pass `--url`:

```dockerfile
CMD if [ -n "$AIRFLOW_URL" ] && [ "$TERMINAIR_DEMO" != "1" ]; then \
      exec python -m terminair --url "$AIRFLOW_URL" ${TERMINAIR_USER:+--user "$TERMINAIR_USER"}; \
    else \
      exec python -m terminair --demo; \
    fi
```

Simpler alternative (sufficient for BLD-03):
```dockerfile
CMD ["sh", "-c", "python -m terminair --url \"$AIRFLOW_URL\" || python -m terminair --demo"]
```

Minimal acceptable fix (always passes AIRFLOW_URL but requires user + password env vars set):
```dockerfile
CMD python -m terminair --url "$AIRFLOW_URL" --user "${TERMINAIR_USER:-admin}"
```

The planner should pick one approach. The cleanest is the conditional form (first option). Note that
the CLI prompts for a password interactively when none is provided — this blocks non-TTY containers.
The entrypoint must either inject `TERMINAIR_PASSWORD` from env or keep `--demo` as the fallback
for the container use case.

**Note:** `VOLUME ["/app/target"]` is already correct for BLD-03's "mounts local target/ directory"
requirement [VERIFIED: Dockerfile read].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal type test for upstream_schema_change | custom mock infrastructure | `ModelState` dataclass + `RegressionAnalyzer.analyze(prev_models=[...])` | The existing pattern in test_regression_and_mock.py lines 147-219 covers all other grain signals with plain ModelState objects |
| Dockerfile entrypoint logic | custom Python launcher | Shell `CMD` with env var expansion | Docker's shell-form CMD handles env substitution without a separate script file |

## Common Pitfalls

### Pitfall 1: Duplicate test IDs after splitting test_regression_and_mock.py
**What goes wrong:** If `TestMockDataProvider` and `TestRegressionAnalyzer` are moved but the old
file is not deleted, pytest collects duplicate test IDs and reports double the count.
**How to avoid:** Delete `test_regression_and_mock.py` after splitting.
**Warning signs:** `pytest --collect-only` shows the same test ID twice.

### Pitfall 2: upstream_schema_change requires upstream_deps populated on ModelState
**What goes wrong:** `RegressionAnalyzer` iterates `model.upstream_deps` (line 165). If the
`ModelState` has `upstream_deps=[]` (the default), `upstream_schema_change` is never triggered.
**How to avoid:** Set `upstream_deps=["model.p.upstream_node"]` on the current model when
constructing the test fixture.

### Pitfall 3: Dockerfile password prompt blocks non-TTY
**What goes wrong:** `cli.py` line 62 calls `click.prompt("Password", hide_input=True)` when
`--url` and `--user` are set but no password is provided. In a container without a TTY, this
blocks forever.
**How to avoid:** The container CMD must include a mechanism to supply the password. Options:
- Use `--demo` only (no password needed)
- Inject `TERMINAIR_PASSWORD` env var and let cli.py pick it up (line 60 already checks it)

### Pitfall 4: test_read_only.py import path for AirflowBridge
**What goes wrong:** `AirflowBridge` lives in `terminair.dbt.airflow_bridge`, not
`terminair.api.airflow_bridge`. An incorrect import path gives `ImportError`.
**Correct import:** `from terminair.dbt.airflow_bridge import AirflowBridge`

## Existing Test Infrastructure

**Framework:** pytest 8.x with pytest-asyncio [VERIFIED: pyproject.toml]

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config | pyproject.toml `[tool.pytest.ini_options]` |
| Test paths | `terminair/tests/` |
| Quick run | `.venv/bin/python -m pytest terminair/tests/ -q` |
| Full suite | `.venv/bin/python -m pytest terminair/tests/ -v` |
| Current count | 112 tests, all passing [VERIFIED: live run] |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest terminair/tests/ -q` |
| Full suite command | `.venv/bin/python -m pytest terminair/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TST-01 | ManifestLoader methods, grain, var(), lineage | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_manifest.py -x` | Yes |
| TST-02 | All 6 RegressionAnalyzer signal types | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_regression.py -x` | No — Wave 0 |
| TST-03 | StateAggregator has_upstream_failure | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_aggregator.py -x` | Yes |
| TST-04 | MockDataProvider tick() transitions | unit | `.venv/bin/python -m pytest terminair/tests/dbt/test_mock_data.py -x` | No — Wave 0 |
| TST-05 | AirflowBridge write-method assertion in test_read_only.py | unit | `.venv/bin/python -m pytest terminair/tests/test_read_only.py -x` | Yes (stub) |
| BLD-01 | dbt-demo target exists and is correct | smoke | `grep "dbt-demo:" Makefile` | Yes |
| BLD-02 | dbt-dev target exists and is correct | smoke | `grep "dbt-dev:" Makefile` | Yes |
| BLD-03 | Dockerfile builds and wires AIRFLOW_URL | smoke | `docker build -t terminair-test .` | Yes (gap in CMD) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest terminair/tests/ -q`
- **Per wave merge:** `.venv/bin/python -m pytest terminair/tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `terminair/tests/dbt/test_regression.py` — covers TST-02 (split from test_regression_and_mock.py + upstream_schema_change)
- [ ] `terminair/tests/dbt/test_mock_data.py` — covers TST-04 (split from test_regression_and_mock.py)
- [x] `terminair/tests/test_read_only.py` — exists but is a stub; extend in Wave 1 task

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 (.venv) | All tests | Yes | 3.11.x | — |
| pytest | Test runner | Yes | 8.x | — |
| Docker | BLD-03 build verification | Yes | 24.x | Skip docker build step in CI |

## Security Domain

No new authentication, cryptography, or external data flows introduced in this phase. All changes
are test files and Dockerfile shell logic. The read-only constraint is explicitly enforced by TST-05.

ASVS not applicable to this phase (test infrastructure + packaging only).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Splitting test_regression_and_mock.py into two files is the correct approach (vs. creating thin re-import files) | Gap 1+2 | Low — both approaches satisfy the file naming requirement; split is cleaner |
| A2 | The Dockerfile's non-demo path should rely on TERMINAIR_PASSWORD env var for password (already handled by cli.py line 60) | Gap 4 | Low — if user forgets to set TERMINAIR_PASSWORD, CLI prompts interactively and blocks the container |

## Open Questions (RESOLVED)

1. **Dockerfile CMD: demo-default vs URL-default**
   - What we know: CMD is `--demo`; BLD-03 says "connects to a configurable Airflow URL"
   - What's unclear: Should the container default to demo mode (safe) or Airflow URL mode (requires env vars)?
   - Recommendation: Default to demo; only use `$AIRFLOW_URL` when `TERMINAIR_DEMO` is explicitly unset and `TERMINAIR_USER` is set. This is safe and matches the BLD-03 intent.
   - RESOLVED: Conditional shell-form CMD — demo-default unless `AIRFLOW_URL` is set and `TERMINAIR_DEMO != 1`. Plan 05-01 Task 3 implements this exactly.

## Sources

### Primary (HIGH confidence)
- `terminair/tests/dbt/test_manifest.py` — read directly, 21 tests verified passing
- `terminair/tests/dbt/test_regression_and_mock.py` — read directly, grep confirmed 0 upstream_schema_change tests
- `terminair/tests/dbt/test_aggregator.py` — read directly, has_upstream_failure coverage confirmed
- `terminair/tests/test_read_only.py` — read directly, placeholder confirmed
- `Makefile` — read directly, dbt-demo and dbt-dev targets confirmed
- `Dockerfile` — read directly, docker build confirmed successful
- `terminair/dbt/airflow_bridge.py` — read directly, zero write methods confirmed
- `.planning/REQUIREMENTS.md` — success criteria and requirement IDs
- Live test run — 112 tests, 0 failures [VERIFIED: `.venv/bin/python -m pytest terminair/tests/ -q`]

## Metadata

**Confidence breakdown:**
- Gap inventory: HIGH — all findings are from direct file reads and live test execution
- Dockerfile fix approach: MEDIUM — shell-form CMD pattern is standard but the exact env var logic is discretionary
- Test split strategy: HIGH — split into named files is the only way to satisfy TST-02 and TST-04 simultaneously

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable codebase, no external dependencies to drift)
