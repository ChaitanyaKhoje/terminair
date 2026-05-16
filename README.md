# Terminair

A read-only k9s-style TUI for dbt model intelligence. Runs locally, correlates your dbt manifest, run results, and Airflow task status in one terminal view — no browser, no dbt Cloud, no write access.

## What It Shows

- **ModelList** — all dbt models with status, tag, duration, row count, row delta, and DAG ID; live tag filter (`t`) and text filter (`/`)
- **Problems** — active failures (upstream-caused vs self-caused) and regression signals (row drops, spikes, grain changes, schema changes) with severity coloring
- **Lineage** — ASCII dependency tree with configurable depth; toggle between model mode and tag/group mode
- **ModelDetail** — 5-tab deep-dive per model: Status, Structure, Variables+Refs, SQL (scrollable), Regression

All screens work against a live dbt project or against built-in demo data with no external services required.

## Quick Start

```bash
# Install
make setup

# Run with demo data (no Airflow, no manifest needed)
make dbt-demo

# Run against your local dbt project
make dbt-dev
```

## Install

```bash
# From source (recommended for development)
git clone https://github.com/chaitanyakhoje/terminair
cd terminair
make setup

# From git tag
pip install git+https://github.com/chaitanyakhoje/terminair@v1.0
```

## Run

```bash
# Demo mode — zero external services, uses built-in fixture data
python3 -m terminair --demo

# Against local dbt artifacts
python3 -m terminair \
  --manifest path/to/target/manifest.json \
  --run-results path/to/target/run_results.json

# With Airflow task status enrichment
python3 -m terminair \
  --manifest path/to/target/manifest.json \
  --run-results path/to/target/run_results.json \
  --dag my_dbt_dag \
  --url http://localhost:8080 \
  --user admin

# Keep password out of shell history
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin
```

## Configuration

Config file: `~/.terminair/config.yaml`

```yaml
connections:
  default:
    url: http://localhost:8080      # Airflow URL (optional)
    auth:
      type: basic
      username: admin
      password: ${TERMINAIR_PASSWORD}
    dbt:
      manifest_path: ~/projects/my_dbt_repo/target/manifest.json
      run_results_path: ~/projects/my_dbt_repo/target/run_results.json
      run_results_previous_path: ~/projects/my_dbt_repo/target/run_results_previous.json
      dag_names:
        - my_dbt_dag
    snowflake:                      # optional — bytes_scanned enrichment
      account: myaccount
      user: myuser
      password: ${SNOWFLAKE_PASSWORD}
      warehouse: COMPUTE_WH
      database: ANALYTICS
      role: DEVELOPER

settings:
  default_connection: default
```

Environment variable placeholders like `${TERMINAIR_PASSWORD}` are expanded on load.

## Key Bindings

| Key | Action |
|-----|--------|
| `1` | ModelList screen |
| `2` | Problems screen |
| `3` | Lineage screen |
| `Enter` | ModelDetail for selected model |
| `1`–`5` | Switch tabs in ModelDetail |
| `t` | Cycle tag filter (ModelList) |
| `m` / `g` | Model mode / group mode (Lineage) |
| `+` / `-` | Expand / collapse depth (Lineage) |
| `/` | Open text filter |
| `Esc` | Back / clear filter |
| `r` | Refresh current screen |
| `:` | Command palette |
| `q` / `Ctrl+C` | Quit |

## Regression Signals

Terminair detects 6 regression signal types by comparing current and previous run results:

| Signal | Severity | Trigger |
|--------|----------|---------|
| `row_drop` | critical | rows written fell >30% |
| `row_spike` | warning | rows written rose >50% |
| `grain_removed` | critical | unique_key column removed |
| `grain_added` | warning | unique_key column added |
| `upstream_schema_change` | warning | upstream model changed grain or materialization |
| `new_model_no_baseline` | info | model has no previous run to compare |

Grain and upstream signals require `run_results_previous_path` to be configured.

## Docker

```bash
docker build -t terminair .

# Demo mode (default when no AIRFLOW_URL set)
docker run --rm terminair

# With Airflow URL
docker run --rm \
  -e AIRFLOW_URL=http://airflow.internal:8080 \
  -e TERMINAIR_USER=admin \
  -e TERMINAIR_PASSWORD=admin \
  -v $(pwd)/target:/app/target \
  terminair
```

## Development

```bash
make setup        # install in editable mode
make dbt-demo     # run against fixture data
make dbt-dev      # run against local target/
make test         # run test suite
```

```bash
uv run pytest terminair/tests/ -v   # 117 tests
```

## Security

- Strictly read-only — `AirflowBridge` and `SnowflakeClient` have zero write methods, enforced by `test_read_only.py`
- No production data — local manifest and run_results only; no dbt Cloud API
- Use environment variables or interactive prompts for secrets

## License

MIT
