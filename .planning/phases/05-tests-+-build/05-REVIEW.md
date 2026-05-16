---
phase: 05-tests-+-build
reviewed: 2026-05-15T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - terminair/tests/dbt/test_regression.py
  - terminair/tests/dbt/test_mock_data.py
  - terminair/tests/test_read_only.py
  - Dockerfile
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 05 split the regression and mock-data tests, added the `upstream_schema_change` test, extended `test_read_only.py` to cover `AirflowBridge`, and rewired the Dockerfile CMD to accept `AIRFLOW_URL`. All 24 tests pass. The test logic itself is largely sound, but there are four structural problems: the Dockerfile CMD has a guaranteed-true condition that makes the demo branch unreachable in the default no-arg case and will hang waiting for a password; the read-only assertion is too narrow (literal HTTP-verb name matching); a silent vacuity in `test_tick_increments_running_duration`; and a missing negative-case guard in the upstream schema change test.

---

## Critical Issues

### CR-01: Dockerfile demo branch is unreachable by default; non-demo invocation hangs waiting for a password

**File:** `Dockerfile:3-21`

**Issue:**
The `ENV` instruction sets `AIRFLOW_URL=http://localhost:8080` as a default. This means `[ -n "$AIRFLOW_URL" ]` is always true — the `else` (demo) branch can never be reached with a plain `docker run <image>`. A bare `docker run terminair` with no environment variables invokes the live-URL path rather than `--demo`, and because `TERMINAIR_USER` is unset, the CMD expands to:

```
python -m terminair --url "http://localhost:8080"
```

The CLI (`cli.py:59`) only prompts for a password when both `url` **and** `user` are set, but in a container without a TTY the prompt will either block forever or raise an EOFError, leaving the image unusable without explicit env-var configuration. More importantly, a first-time user who runs the image with no arguments expecting a self-contained demo will get a broken live-connection attempt, not a demo.

The two conditions (`AIRFLOW_URL` non-empty AND `TERMINAIR_DEMO != "1"`) were designed as independent gates, but the non-empty check is made vacuous by the `ENV` default.

**Fix:**

Remove the default from `ENV` so the gate behaves as intended, and add `TERMINAIR_PASSWORD` pass-through for non-demo runs:

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# AIRFLOW_URL intentionally has NO default — absence triggers --demo mode

CMD if [ -n "$AIRFLOW_URL" ] && [ "$TERMINAIR_DEMO" != "1" ]; then \
      exec python -m terminair \
        --url "$AIRFLOW_URL" \
        ${TERMINAIR_USER:+--user "$TERMINAIR_USER"} \
        ${TERMINAIR_PASSWORD:+--password "$TERMINAIR_PASSWORD"}; \
    else \
      exec python -m terminair --demo; \
    fi
```

Users who want the live-URL mode must now pass `-e AIRFLOW_URL=...`; users who want demo mode run the image bare or with `-e TERMINAIR_DEMO=1`. This matches the intuitive contract.

---

## Warnings

### WR-01: test_read_only.py checks only four literal HTTP-verb method names — write methods with any other name escape detection

**File:** `terminair/tests/test_read_only.py:13`

**Issue:**
The assertion filters the member list to exactly `("post", "put", "delete", "patch")`. A developer who adds a write method named anything else — `create_dag_run`, `trigger`, `enable_dag`, `_post_json`, `unpause` — will not be caught. The contract documented in CLAUDE.md is "zero write methods (GET only)", which is a broader semantic guarantee than "no method literally named post/put/delete/patch".

Additionally, `inspect.isfunction` on a class skips `classmethod` and `staticmethod` descriptors; a write method disguised as a staticmethod would not appear in `members` at all.

```python
# Current — too narrow
members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
```

**Fix:**
Scan for HTTP write semantics by inspecting actual calls inside each method's source, or at minimum broaden the name scan to common write-operation prefixes and also include `ismethod`:

```python
import inspect, ast, textwrap

WRITE_PREFIXES = ("post", "put", "delete", "patch", "create", "update",
                  "trigger", "enable", "disable", "unpause", "clear")
WRITE_HTTP_METHODS = {"post", "put", "delete", "patch"}

def _source_calls_write_http(fn) -> bool:
    """Return True if the function source contains .post(/.put(/.delete(/.patch( calls."""
    try:
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in WRITE_HTTP_METHODS:
            return True
    return False

members = inspect.getmembers(AirflowBridge, predicate=inspect.isroutine)
violations = [
    name for name, fn in members
    if not name.startswith("_") and (
        any(name.lower().startswith(p) for p in WRITE_PREFIXES)
        or _source_calls_write_http(fn)
    )
]
assert not violations, f"Found write methods on AirflowBridge: {violations}"
```

This is defence-in-depth — the current `AirflowBridge` is clean, but the test is supposed to prevent future regressions.

---

### WR-02: test_tick_increments_running_duration silently makes no assertions if a model transitions away from "running" mid-tick

**File:** `terminair/tests/dbt/test_mock_data.py:100-104`

**Issue:**
The test captures `initial_durations` for all `status == "running"` models before the tick, then re-queries `after_durations` for `status == "running"` models after the tick. The inner loop guards with `if name in after_durations`, which silently skips any model that is no longer running after the tick. If a tick boundary causes a transition (e.g., tick count 4, 8, …), the assertion simply never fires and the test passes vacuously for that model.

In the current code this only matters at multiples of 4, and tick=1 is safe, but the guard means the test cannot detect a bug where `tick()` transitions a model at tick=1 without incrementing its duration.

```python
# Lines 100-104 — the guard makes the assertion vacuous for transitioned models
for name, initial_dur in initial_durations.items():
    if name in after_durations:          # silent skip if model transitioned
        assert after_durations[name] > (initial_dur or 0.0), ...
```

**Fix:**
Split the assertion: verify duration increased for models that are still running, and separately verify that any model that transitioned has a final `duration_s` greater than its pre-tick value (read from `models_after` regardless of status):

```python
after_by_name = {m.name: m for m in models_after}
for name, initial_dur in initial_durations.items():
    m_after = after_by_name[name]   # model must still exist
    assert m_after.duration_s is not None
    assert m_after.duration_s > (initial_dur or 0.0), (
        f"{name} duration did not increase after tick"
    )
```

---

### WR-03: upstream_schema_change test also passes curr_upstream (with rows_previous=None + status=success) in the current list, generating an extra new_model_no_baseline signal that is not accounted for

**File:** `terminair/tests/dbt/test_regression.py:355-360`

**Issue:**
The test constructs `curr_upstream` with `rows_previous` defaulting to `None` (via `ModelState` field default) and `status="success"`. `RegressionAnalyzer.analyze()` will therefore emit both an `upstream_schema_change` signal on `fct_orders` (the intent) **and** a `new_model_no_baseline` signal on `stg_orders` (the upstream itself). The test only asserts `len(upstream_changes) == 1` against the filtered `upstream_schema_change` slice, which passes — but it does not assert that no spurious signals appear on the upstream node, and it does not assert `len(signals) == 1` overall.

This is not a test failure in the current codebase, but if the implementation is changed to suppress `new_model_no_baseline` when a previous snapshot exists (a reasonable future refinement), the test would not catch the regression because it never validated the total signal count.

**Fix:**
Add explicit assertions on total signal count and absence of unexpected signals on the upstream node:

```python
# After the existing assertions:
assert upstream_changes[0].severity == Severity.WARNING
assert upstream_changes[0].node_id == "model.p.fct_orders"

# Guard: no upstream_schema_change on the upstream node itself
upstream_self_signals = [
    s for s in signals
    if s.node_id == "model.p.stg_orders" and s.signal_type == "upstream_schema_change"
]
assert len(upstream_self_signals) == 0, (
    "upstream node should not emit upstream_schema_change against itself"
)
```

---

## Info

### IN-01: test_regression.py re-imports from terminair.dbt.regression inside every test method — consider module-level or class-level imports

**File:** `terminair/tests/dbt/test_regression.py:16-17` (repeated across all 12 test methods)

**Issue:**
Every test method performs the same `from terminair.dbt.regression import RegressionAnalyzer` and `from terminair.dbt.models import ModelState` inside the function body. This is not wrong — Python caches module imports in `sys.modules` — but it makes the test file harder to read and creates noise when scanning for import errors, since a failure in `test_import` does not prevent the same import line from being re-executed in every subsequent test.

**Fix:**
Move the common imports to module level at the top of the file. The existing `test_import` sentinel test can be removed or replaced with a simpler `import terminair.dbt.regression` check that doesn't duplicate what the other tests already exercise:

```python
# Top of file
from terminair.dbt.regression import RegressionAnalyzer
from terminair.dbt.models import ModelState, Severity
```

---

_Reviewed: 2026-05-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
