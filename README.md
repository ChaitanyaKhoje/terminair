# Terminair

A terminal UI for dbt model intelligence. See what's running, what failed, and why — without leaving your terminal.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## Install

```bash
pip install terminair
```

Requires Python 3.11+.

## Try it in 30 seconds

No dbt project needed — run against built-in demo data:

```bash
terminair --demo
```

## Connect to your dbt project

Point it at your local `target/` directory after a `dbt run`:

```bash
terminair \
  --manifest ~/my-dbt-project/target/manifest.json \
  --run-results ~/my-dbt-project/target/run_results.json
```

For regression signals (row drops, grain changes), also provide the previous run:

```bash
terminair \
  --manifest target/manifest.json \
  --run-results target/run_results.json \
  --run-results-previous target/run_results_previous.json
```

## What you get

| Screen | Key | What it shows |
|--------|-----|---------------|
| Models | `1` | All models — status, rows, row delta, duration, DAG ID |
| Problems | `2` | Failures (upstream vs self-caused) + regression signals |
| Lineage | `3` | ASCII dependency tree with configurable depth |
| Detail | `Enter` | 5-tab deep-dive: Status, Structure, Refs, SQL, Regression |

**Regression signals detected:**

| Signal | Severity |
|--------|----------|
| Row count dropped >30% | critical |
| Row count spiked >50% | warning |
| Grain column removed | critical |
| Grain column added | warning |
| Upstream schema changed | warning |
| New model with no baseline | info |

## Navigation

```
1 / 2 / 3   Switch screens
Enter        Open model detail
1-5          Switch tabs in detail view
t            Cycle tag filter
/            Text filter
Esc          Back / clear filter
r            Refresh
:            Command palette
q            Quit
```

## Add Airflow task status

If you run dbt via Airflow, pass your DAG name to enrich models with live task status:

```bash
terminair \
  --manifest target/manifest.json \
  --run-results target/run_results.json \
  --dag my_dbt_dag \
  --url http://localhost:8080 \
  --user admin
# Password prompted, or: export TERMINAIR_PASSWORD=admin
```

## Config file

For persistent settings, create `~/.terminair/config.yaml`:

```yaml
connections:
  default:
    url: http://localhost:8080        # Airflow (optional)
    auth:
      type: basic
      username: admin
      password: ${TERMINAIR_PASSWORD} # env var expanded automatically
    dbt:
      manifest_path: ~/projects/my-dbt/target/manifest.json
      run_results_path: ~/projects/my-dbt/target/run_results.json
      run_results_previous_path: ~/projects/my-dbt/target/run_results_previous.json
      dag_names:
        - my_dbt_dag
    snowflake:                        # optional — bytes_scanned enrichment
      account: myaccount
      user: myuser
      password: ${SNOWFLAKE_PASSWORD}
      warehouse: COMPUTE_WH
      database: ANALYTICS
      role: DEVELOPER

settings:
  default_connection: default
```

Then just run:

```bash
terminair
```

## Run from source

```bash
git clone https://github.com/chaitanyakhoje/terminair
cd terminair
pip install -e ".[dev]"
terminair --demo
```

## Docker

```bash
docker build -t terminair .

# Demo mode
docker run --rm -it terminair

# With Airflow
docker run --rm -it \
  -e AIRFLOW_URL=http://airflow.internal:8080 \
  -e TERMINAIR_USER=admin \
  -e TERMINAIR_PASSWORD=secret \
  -v $(pwd)/target:/app/target \
  terminair
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # 117 tests
```

## License

MIT
