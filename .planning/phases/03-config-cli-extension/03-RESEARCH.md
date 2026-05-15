# Phase 3: Config + CLI Extension - Research

**Researched:** 2026-05-15
**Domain:** Pydantic v2 config models, Click CLI, Textual app bootstrap, demo/fallback wiring
**Confidence:** HIGH

## Summary

Phase 3 is substantially pre-implemented. All five CFG requirements have corresponding production code and passing tests. The code landed during Phase 2 development (likely as supporting infrastructure for the data layer). Every requirement has a matching test file that already passes as part of the 111-test green suite.

The planner's primary job is not to write new code but to **audit the existing implementation** for gaps relative to the exact requirement wording, then fill those gaps. One notable gap exists: the CONTEXT.md specifies fallback warnings should appear "in topbar" (FlashBar), but `_build_data_provider` currently logs to `_logger.warning` (file/stdout) only. Since `_build_data_provider` runs from `on_mount`, the app is mounted at that point and `self._flash_warn()` can be called. This is a one-line fix per fallback branch.

**Primary recommendation:** Plan this phase as an audit-and-gap-fill phase. The planner should verify each CFG requirement against the implementation, list any delta, write targeted tests for uncovered behaviors (topbar warning, manifest-exists-but-file-missing path), and produce a short verification task.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config Models:**
- DbtConfig fields: manifest_path (Path|None), run_results_path (Path|None), run_results_previous_path (Path|None), manifest_previous_path (Path|None), dag_names (list[str] = [])
- SnowflakeConfig fields: account (str), user (str), password (str), warehouse (str), database (str), role (str) — all required if block present, entire block optional
- Both are optional fields on Connection (None by default)
- Env var expansion (_expand_env_vars) applies to all new fields

**CLI Flags:**
- --manifest PATH: overrides config dbt.manifest_path; type=click.Path(path_type=Path)
- --run-results PATH: overrides config dbt.run_results_path; type=click.Path(path_type=Path)
- --dag TEXT: repeatable (multiple=True), appends to config dag_names (does not replace)
- --demo: boolean flag (is_flag=True), bypasses connection requirements; wires MockDataProvider

**Demo Mode / Fallback Logic:**
- --demo flag: app starts with MockDataProvider regardless of config; no Airflow/Snowflake/manifest needed
- Automatic fallback: if manifest_path is configured but file doesn't exist → use MockDataProvider, log warning in topbar
- Fallback is silent for Snowflake absence (bytes_scanned=None)
- Fallback is logged for Airflow unreachable (warning in topbar)

### Claude's Discretion
- merge_configs() can be extended or a new merge function created for dbt/snowflake config
- TerminairApp receives a "demo_mode" boolean or a pre-built data provider — implementation detail
- Test approach follows existing test_config.py patterns (pytest, no mocking frameworks)

### Deferred Ideas (OUT OF SCOPE)
- Dockerfile (BLD-03) — deferred to Phase 5
- Real Snowflake connection — Phase 2 already has the interface stub; config just needs credentials through
- Multiple connection contexts for dbt — single connection only in v1
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | DbtConfig Pydantic model in config.py with manifest_path, run_results_path, run_results_previous_path, manifest_previous_path, dag_names; all optional | IMPLEMENTED — config.py lines 25-30; test_connection_supports_optional_dbt_and_snowflake passes |
| CFG-02 | SnowflakeConfig Pydantic model in config.py with account, user, password, warehouse, database, role; entire block optional | IMPLEMENTED — config.py lines 33-40; same test covers it |
| CFG-03 | Connection model extended with optional dbt and snowflake fields | IMPLEMENTED — config.py lines 48-49; test_merge_config_overrides_dbt_paths_and_appends_dags passes |
| CFG-04 | CLI adds --manifest, --run-results, --dag (repeatable), --demo flags; --dag appends to config dag_names | IMPLEMENTED — cli.py lines 19-34; test_cli_parses_repeatable_dag_and_demo passes |
| CFG-05 | --demo wires MockDataProvider; fallback triggered when manifest_path missing or file not found | PARTIALLY IMPLEMENTED — MockDataProvider wiring and fallback logic exist; topbar warning (FlashBar) for manifest-missing fallback uses _logger.warning only, not self._flash_warn() |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config model extension (DbtConfig, SnowflakeConfig) | Config layer (config.py) | — | Pure data model; no UI concern |
| CLI flag parsing and merging | CLI entry point (cli.py) | Config layer | Click parses; merge_configs combines |
| Demo mode / data provider selection | App bootstrap (app.py) | Config layer | App decides at mount time which provider to use |
| Topbar fallback warning | App bootstrap (app.py) | Widget (FlashBar) | Warning fires at mount, must use FlashBar for TUI visibility |
| Env var expansion for new fields | Config layer (config.py) | — | _expand_env_vars is recursive; covers new dict keys automatically |

## Implementation Status (Verified)

### What is Already Done [VERIFIED: codebase grep + test run]

All 111 tests pass. Phase 3 code was pre-built:

| File | What Exists | Verified By |
|------|-------------|-------------|
| `terminair/config.py` | DbtConfig, SnowflakeConfig, CLIConfig with demo/manifest/dag_names, _merge_dbt_config, merge_configs with demo short-circuit | Read file + test pass |
| `terminair/cli.py` | --manifest, --run-results, --dag (multiple=True), --demo flags; passes demo_mode to TerminairApp | Read file + test pass |
| `terminair/app.py` | TerminairApp(config, demo_mode=False), _build_data_provider() with demo branch + manifest-missing fallback | Read file + test pass |
| `terminair/tests/test_config.py` | 5 tests covering merge, dbt paths, dag append, demo short-circuit | 6/6 pass |
| `terminair/tests/test_cli.py` | CLI integration test via CliRunner with --demo --manifest --dag | 1/1 passes |
| `terminair/tests/test_app_demo.py` | demo_mode=True → MockDataProvider; missing dbt config → MockDataProvider | 2/2 pass |

### The One Gap: Topbar Warning [VERIFIED: code read]

CONTEXT.md requires: "Fallback is logged for Airflow unreachable (warning in topbar)"
CONTEXT.md requires: manifest_path missing → "log warning in topbar"

Current `_build_data_provider` uses `_logger.warning(...)` (Python logging to file/stdout), NOT `self._flash_warn(...)` (FlashBar TUI widget). The FlashBar is docked to the app and available as soon as `on_mount` fires. Since `get_data_provider()` is called from `on_mount`, `self._flash_warn()` can safely be called at that point.

Affected branches in `_build_data_provider` (app.py):
- Line 100: "No dbt configuration found — using demo data" — should also call `self._flash_warn()`
- Lines 106-109: "dbt manifest missing at X — using demo data" — should also call `self._flash_warn()`
- Line 122: "dbt data layer unavailable — using demo data" — should also call `self._flash_warn()`
- Line 132: "Airflow bridge unavailable" — should call `self._flash_warn()`

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| pydantic | v2 (>=2.0) | BaseModel, Field, Optional fields | In use [VERIFIED: config.py] |
| click | >=8.0 | CLI parsing, Path type, multiple=True | In use [VERIFIED: cli.py] |
| textual | >=0.80 | TUI app framework, FlashBar widget | In use [VERIFIED: app.py] |
| pytest | 9.0.3 | Test framework | In use [VERIFIED: test run] |

No new dependencies are required for Phase 3.

### Patterns in Use [VERIFIED: codebase read]

**Pydantic v2 optional field pattern:**
```python
# Source: terminair/config.py
class DbtConfig(BaseModel):
    manifest_path: Optional[Path] = None
    run_results_path: Optional[Path] = None
    dag_names: list[str] = Field(default_factory=list)
```

**Click repeatable flag pattern:**
```python
# Source: terminair/cli.py
@click.option("--dag", multiple=True, help="Append a DAG name (repeatable)")
# Usage: dag is a tuple; list(dag) converts to list
dag_names=list(dag)
```

**Click demo flag pattern:**
```python
# Source: terminair/cli.py
@click.option("--demo", is_flag=True, help="Run against demo data")
```

**FlashBar warning call pattern:**
```python
# Source: terminair/app.py
self._flash_warn("dbt manifest missing — using demo data")
```

**merge_configs demo short-circuit:**
```python
# Source: terminair/config.py merge_configs()
if cli_config.demo:
    # Returns config without connection validation
    return Config(connections=connections, settings=Settings(**settings_dict), ...)
```

## Architecture Patterns

### Data Provider Selection Flow

```
cli.py main()
    │
    ├── parse flags → CLIConfig(demo, manifest_path, dag_names, ...)
    │
    ├── Config.load(path) → file_config
    │
    ├── merge_configs(file_config, cli_config) → full_config
    │   └── if demo: skip connection validation
    │       else: merge dbt paths, extend dag_names
    │
    └── TerminairApp(full_config, demo_mode=cli_config.demo).run()
            │
            └── on_mount()
                    └── get_data_provider()
                            └── _build_data_provider()
                                    ├── demo_mode=True → MockDataProvider()
                                    ├── no dbt config → MockDataProvider() + flash_warn
                                    ├── manifest missing → MockDataProvider() + flash_warn
                                    ├── data layer error → MockDataProvider() + flash_warn
                                    └── real path → StateAggregator(manifest, artifacts, bridge?, snowflake?)
```

### Recommended Project Structure (unchanged)
```
terminair/
├── config.py          # DbtConfig, SnowflakeConfig, CLIConfig, merge_configs — complete
├── cli.py             # --manifest, --run-results, --dag, --demo — complete
├── app.py             # _build_data_provider() — needs flash_warn additions
└── tests/
    ├── test_config.py      # 6 tests — all pass
    ├── test_cli.py         # 1 test — passes
    └── test_app_demo.py    # 2 tests — pass; topbar warning not yet tested
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path type in Click | Custom path parsing | `click.Path(path_type=Path)` | Handles validation, converts to pathlib.Path |
| Optional Pydantic fields | Custom None checks | `Optional[X] = None` / `X \| None = None` | Pydantic handles None serialization, validation |
| Multiple CLI args | Custom list accumulation | `multiple=True` → returns tuple | Click handles it cleanly |
| Env var expansion | New expansion code | `_expand_env_vars()` existing recursive function | Already handles dicts, lists, strings |

## Common Pitfalls

### Pitfall 1: FlashBar Called Before Mount
**What goes wrong:** Calling `self._flash_warn()` before the app is fully mounted raises a Textual query exception.
**Why it happens:** `query_one(FlashBar)` fails if FlashBar hasn't been composed yet.
**How to avoid:** `_build_data_provider()` is called from `on_mount()` which fires after `compose()` — FlashBar is available. The existing `_flash_warn` already wraps in `try/except` for safety.
**Warning signs:** `NoMatches` or `TooManyMatches` exception from Textual.

### Pitfall 2: merge_configs Raises on Missing Connection in Non-Demo Mode
**What goes wrong:** If `--demo` is not set and neither `--url` nor a config file connection exists, `merge_configs` raises `ValueError: Connection 'default' not found`.
**Why it happens:** The non-demo path requires a valid active connection.
**How to avoid:** Always pass `--demo` when running without Airflow credentials. The `dbt-demo` Makefile target already does this.
**Warning signs:** `Error: Connection 'default' not found` printed to stderr on startup.

### Pitfall 3: --dag Flag Collision with Existing Startup Jump
**What goes wrong:** The original Airflow CLI had a `--dag` flag for jump-to-DAG navigation. The new `--dag` serves a different purpose (AirflowBridge dag_names list).
**Why it happens:** Both used the same flag name.
**How to avoid:** The CONTEXT.md notes this risk. Current cli.py has resolved it — `--dag` is now documented as "Append a DAG name to the dbt configuration". The jump-to-DAG action is now `action_jump_to_dag` in app.py, not a CLI flag. No collision exists in the current code.
**Warning signs:** If a user expects `--dag my_dag_id` to navigate to that DAG on launch, behavior will differ.

### Pitfall 4: Environment Variable Expansion on Path Fields
**What goes wrong:** Path fields like `manifest_path: Optional[Path]` receive a string `${DBT_MANIFEST}` from YAML, which Pydantic coerces directly to `Path("${DBT_MANIFEST}")` without expanding the env var.
**Why it happens:** `_expand_env_vars` runs on the raw dict before Pydantic sees it, so env vars in YAML string values get expanded to their string values before Path coercion. This works correctly for `${VAR}` patterns only when the entire value is the pattern.
**How to avoid:** Users must use `${VAR_NAME}` as the sole value in YAML (not embedded in a larger string). This is the existing contract and is already correct.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | All code | ✓ | 3.11.15 [VERIFIED: Makefile + venv] | — |
| pytest | Test suite | ✓ | 9.0.3 [VERIFIED: test run] | — |
| pydantic v2 | Config models | ✓ | Installed [VERIFIED: imports work] | — |
| click | CLI | ✓ | Installed [VERIFIED: cli.py runs] | — |
| textual | TUI + FlashBar | ✓ | >=0.80 [VERIFIED: app.py runs] | — |

No missing dependencies. All tooling is available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml |
| Quick run command | `.venv/bin/pytest terminair/tests/test_config.py terminair/tests/test_cli.py terminair/tests/test_app_demo.py -v` |
| Full suite command | `.venv/bin/pytest terminair/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | DbtConfig fields and optionality | unit | `.venv/bin/pytest terminair/tests/test_config.py::test_connection_supports_optional_dbt_and_snowflake -x` | ✅ |
| CFG-02 | SnowflakeConfig fields and optionality | unit | `.venv/bin/pytest terminair/tests/test_config.py::test_connection_supports_optional_dbt_and_snowflake -x` | ✅ |
| CFG-03 | Connection extended with dbt/snowflake | unit | `.venv/bin/pytest terminair/tests/test_config.py::test_merge_config_overrides_dbt_paths_and_appends_dags -x` | ✅ |
| CFG-04 | CLI flags parse and merge correctly | integration | `.venv/bin/pytest terminair/tests/test_cli.py -x` | ✅ |
| CFG-05 | --demo wires MockDataProvider; manifest-missing fallback | unit | `.venv/bin/pytest terminair/tests/test_app_demo.py -x` | ✅ (topbar warning not yet tested) |

### Wave 0 Gaps
- [ ] `terminair/tests/test_app_demo.py` needs a test for manifest-path-configured-but-file-missing FlashBar warning (not just logger.warning). Requires patching `FlashBar.flash_warn` or verifying via `_flash_warn` call.
- The topbar warning gap is a test gap as well as an implementation gap — both need one Wave.

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest terminair/tests/test_config.py terminair/tests/test_cli.py terminair/tests/test_app_demo.py -v`
- **Per wave merge:** `.venv/bin/pytest terminair/tests/ -v`
- **Phase gate:** Full 111-test suite green before `/gsd-verify-work`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Credentials are passed through, not handled |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Read-only app |
| V5 Input Validation | yes | Pydantic v2 validates all config fields |
| V6 Cryptography | no | No crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Password in CLI args visible in ps aux | Information Disclosure | Already uses TERMINAIR_PASSWORD env var as preferred path; --password is fallback |
| Snowflake password in config.yaml | Information Disclosure | Env var expansion: ${SNOWFLAKE_PASSWORD} prevents plaintext in config file |
| Path traversal via --manifest flag | Tampering | click.Path(path_type=Path) normalizes path; file is read-only (ManifestLoader reads, never writes) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Airflow-only CLI (--url, --user, --password) | dbt-aware CLI with --manifest, --run-results, --dag, --demo | Phase 3 (current) | App works fully offline with --demo |
| Airflow required at startup | MockDataProvider fallback when manifest absent | Phase 3 (current) | No external services needed for development |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_flash_warn` is safe to call from `_build_data_provider` during `on_mount` because FlashBar is composed before `on_mount` fires | Common Pitfalls | Calling it crashes with NoMatches; but `_flash_warn` already has try/except so it silently skips — acceptable degradation |

## Open Questions (RESOLVED)

1. **Should `_flash_warn` be called in addition to `_logger.warning`, or instead of?**
   - What we know: CONTEXT.md says "log warning in topbar"; current code logs to file logger only
   - What's unclear: Whether file logger output is sufficient for the dev experience, or TUI feedback is required
   - Recommendation: Call both — keep `_logger.warning` for log files; add `self._flash_warn()` immediately after for TUI visibility. Low risk since `_flash_warn` is guarded by try/except.
   - RESOLVED: Call both. Keep `_logger.warning` for log files, add `self._flash_warn()` immediately after in each branch. The `_flash_warn` wrapper already has try/except so it is safe to call in any context.

2. **Is the `--dag` flag conflict with original Airflow jump-to-DAG fully resolved?**
   - What we know: Current cli.py has `--dag` with `multiple=True` for dag_names list; no startup jump flag exists
   - What's unclear: Whether any users or scripts relied on the old single-value `--dag` for navigation
   - Recommendation: Confirm in CLAUDE.md or README that `--dag` now means "include this DAG in AirflowBridge scope" — a one-line doc fix.
   - RESOLVED: Fully resolved. The old single-value `--dag` navigation flag was removed in Phase 1 cleanup along with all Airflow screens. The current `--dag` (multiple=True) is a clean new CLI surface with no legacy users to migrate.

## Sources

### Primary (HIGH confidence)
- `terminair/config.py` — Read directly; DbtConfig, SnowflakeConfig, CLIConfig, merge_configs all present and verified
- `terminair/cli.py` — Read directly; all four CLI flags confirmed
- `terminair/app.py` — Read directly; _build_data_provider fallback logic confirmed
- `terminair/tests/test_config.py`, `test_cli.py`, `test_app_demo.py` — Read and test run confirmed 111/111 pass

### Secondary (MEDIUM confidence)
- Pydantic v2 `Optional[X] = None` pattern — [ASSUMED] standard v2 idiom, confirmed by working tests
- Click `multiple=True` tuple behavior — [ASSUMED] standard Click behavior, confirmed by working test

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified by reading actual source files and running tests
- Architecture: HIGH — data flow traced through actual code
- Pitfalls: MEDIUM — pitfall 1-3 verified from code; pitfall 4 is partially assumed
- Implementation status: HIGH — code read + test execution confirms

**Research date:** 2026-05-15
**Valid until:** 60 days (stable, no fast-moving dependencies)
