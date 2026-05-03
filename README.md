# Terminair

A read-only k9s-style TUI for Apache Airflow.

## What It Shows

- DAG overview with state, owner, schedule, next run, and bookmark markers
- Combined errors view for failed runs and import errors
- Pools, health, SLA misses, resource timeline, and watchlist
- DAG drill-in with run history, task instances, task history, dataset dependencies, and XComs
- Read-only API access only; no triggers, clears, or other write actions

## Install

For local development:

```bash
make setup
```

For runtime-only use:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

## Run

The app needs a running Airflow instance with the REST API enabled.

For a zero-setup demo, `make demo` will clone the public example Airflow repo into `.demo/airflow-dag-template`, start its Docker stack, and then launch Terminair against it.

```bash
# Recommended: keep the password out of shell history
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin
```

You can also use a named connection from config:

```bash
python3 -m terminair --ctx production
```

Helpful commands:

```bash
make help
make setup
make airflow-up
make demo
.venv/bin/python -m terminair --help
.venv/bin/python -m terminair --version
```

## Authentication

Basic auth is the most common setup:

```bash
# Option 1: environment variable
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin

# Option 2: interactive prompt
python3 -m terminair --url http://localhost:8080 --user admin
# Password is hidden when prompted.

# Option 3: CLI argument for local development only
python3 -m terminair --url http://localhost:8080 --user admin --password admin
```

Token auth works through config files and environment substitution:

```yaml
# ~/.terminair/config.yaml
connections:
  production:
    url: https://airflow.company.com
    auth:
      type: token
      token: ${AIRFLOW_PROD_TOKEN}
```

```bash
export AIRFLOW_PROD_TOKEN=your-bearer-token
python3 -m terminair --ctx production
```

## Configuration

Config is loaded from `~/.terminair/config.yaml`, or from `$XDG_CONFIG_HOME/terminair/config.yaml` when `XDG_CONFIG_HOME` is set.

Supported settings in the current build:

```yaml
connections:
  default:
    url: http://localhost:8080
    auth:
      type: basic
      username: admin
      password: admin

settings:
  default_connection: default
  watchlist:
    - my_critical_dag
    - daily_revenue_pipeline
  show_sensitive: false
```

Notes:

- `show_sensitive: true` or `TERMINAIR_SHOW_SENSITIVE=1` reveals XCom previews.
- Environment-variable placeholders like `${AIRFLOW_PROD_TOKEN}` are expanded on load.
- `--refresh` overrides the configured refresh interval.

## Navigation

From the DAGs screen:

| Key | Action |
|-----|--------|
| `1` | Errors view |
| `2` | Pools |
| `3` | Health |
| `4` | SLA misses |
| `5` | Resource timeline |
| `0` | Watchlist |
| `Enter` | Drill into the selected DAG |
| `Esc` | Back / clear filter |
| `/` | Filter the DAG list |
| `r` | Refresh current screen |
| `b` | Bookmark / unbookmark selected DAG |
| `w` | Toggle wrapped columns in the DAG table |
| `h` | Task history |
| `d` | Dataset dependencies |
| `x` | XCom viewer |
| `:` | Command palette |
| `q` / `Ctrl+C` | Quit |

Command palette shortcuts currently wired in the app:

- `:errors`
- `:pools`
- `:health`
- `:recent`

## Airflow Setup

Terminair requires the Airflow REST API to be enabled. For Airflow 2.x, make sure `airflow.cfg` includes:

```ini
[api]
auth_backends = airflow.api.auth.backend.basic_auth
```

The demo workflow clones a local cache of the example Airflow stack under `.demo/airflow-dag-template`. Its Docker Compose setup creates an `admin/admin` account, a few pools, and sample DAGs that exercise the UI.

For managed Airflow environments, use the token auth flow above and point Terminair at the right connection.

## Security

- Read-only API client: no trigger, clear, patch, or delete methods are implemented.
- Prefer environment variables or interactive prompts for secrets.
- Debug logging is disabled by default. Set `TERMINAIR_DEBUG=1` to enable it.

## Testing

```bash
python3 -m pytest terminair/tests/ -v
```

## License

MIT
