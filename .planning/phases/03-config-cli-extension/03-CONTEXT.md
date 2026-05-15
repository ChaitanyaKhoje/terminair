# Phase 3: Config + CLI Extension - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Extend `terminair/config.py` with `DbtConfig` and `SnowflakeConfig` Pydantic models, add optional `dbt` and `snowflake` fields to the `Connection` model, and add four new CLI flags to `terminair/cli.py`: `--manifest`, `--run-results`, `--dag` (repeatable), and `--demo`. The `--demo` flag wires the app to `MockDataProvider` with no external services required. If `manifest_path` is missing or the file doesn't exist, the app automatically falls back to `MockDataProvider`.

Files to modify:
- `terminair/config.py` — add DbtConfig, SnowflakeConfig, extend Connection
- `terminair/cli.py` — add --manifest, --run-results, --dag, --demo flags
- `terminair/__main__.py` — wire demo mode if applicable

</domain>

<decisions>
## Implementation Decisions

### Config Models
- DbtConfig Pydantic model fields: manifest_path (Path|None), run_results_path (Path|None), run_results_previous_path (Path|None), manifest_previous_path (Path|None), dag_names (list[str] = [])
- SnowflakeConfig Pydantic model fields: account (str), user (str), password (str), warehouse (str), database (str), role (str) — all required if block present, but entire block is optional
- Both DbtConfig and SnowflakeConfig are optional fields on Connection (None by default)
- Env var expansion (existing _expand_env_vars) applies to all new fields

### CLI Flags
- --manifest PATH: overrides config dbt.manifest_path; type=click.Path(path_type=Path)
- --run-results PATH: overrides config dbt.run_results_path; type=click.Path(path_type=Path)
- --dag TEXT: repeatable (multiple=True), appends to config dag_names (does not replace)
- --demo: boolean flag (is_flag=True), bypasses all connection requirements; wires MockDataProvider

### Demo Mode / Fallback Logic
- --demo flag: app starts with MockDataProvider regardless of config; no Airflow/Snowflake/manifest needed
- Automatic fallback: if manifest_path is configured but file doesn't exist → use MockDataProvider, log warning in topbar
- Fallback is silent for Snowflake absence (bytes_scanned=None)
- Fallback is logged for Airflow unreachable (warning in topbar)

### Claude's Discretion
- merge_configs() can be extended or a new merge function created for dbt/snowflake config
- TerminairApp receives a "demo_mode" boolean or a pre-built data provider — implementation detail
- Test approach follows existing test_config.py patterns (pytest, no mocking frameworks)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `terminair/config.py` — Config, Connection, Settings, ConnectionAuthBasic/Token, merge_configs(), _expand_env_vars()
- `terminair/cli.py` — existing Click @click.command() with url/user/password/ctx/config/dag/refresh/version options
- `terminair/dbt/mock_data.py` — MockDataProvider with async get_models() and tick()
- `terminair/dbt/aggregator.py` — StateAggregator (real data path)
- `terminair/logging_utils.py` — get_logger pattern

### Established Patterns
- Pydantic v2 BaseModel for all config models
- Optional fields use `type | None = None` syntax (Python 3.11+)
- Env var expansion: `${VAR_NAME}` strings expanded by _expand_env_vars()
- Click options with type=click.Path(path_type=Path) for file paths
- merge_configs() merges file_config + cli_config → final Config

### Integration Points
- TerminairApp.__init__(config) receives the merged Config — needs demo_mode awareness
- Connection.dbt gives access to DbtConfig at runtime
- Phase 4 screens will call StateAggregator or MockDataProvider depending on demo mode
- CLAUDE.md constraint: Makefile targets dbt-demo and dbt-dev added in Phase 5

</code_context>

<specifics>
## Specific Ideas

- --dag flag in cli.py already exists (used for jump-to-DAG startup) — check if it conflicts; if so rename the new one to --dag-name or ensure they serve different purposes. The new --dag is for AirflowBridge dag_names list, the existing --dag was for startup navigation. May need to reconcile.
- Config env var expansion should handle ${SNOWFLAKE_ACCOUNT} etc. — already works via _expand_env_vars
- CLIConfig model may need new fields: manifest_path, run_results_path, dag_names (list), demo (bool)
- If --demo is set, merge_configs() should short-circuit connection validation (no URL required)

</specifics>

<deferred>
## Deferred Ideas

- Dockerfile (BLD-03) — deferred to Phase 5
- Real Snowflake connection — Phase 2 already has the interface stub; config just needs to pass credentials through
- Multiple connection contexts for dbt — single connection only in v1

</deferred>
