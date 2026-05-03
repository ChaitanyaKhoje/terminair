# Terminair

A k9s-style TUI for Apache Airflow — read-only terminal interface for monitoring and debugging DAGs.

## Features

### Navigation & Views
- **DAGs overview** — All DAGs with status, schedule, owner, next run, active state
- **Recent Activity** — Feed of the latest DAG runs across all DAGs
- **Run History** — Per-DAG run list with duration, drift vs average, error column
- **Task Instances** — Task states for a specific run, sorted by priority (failed first)
- **Task History** — Cross-run pass/fail pattern to identify flaky tasks
- **DAG Graph** — ASCII dependency graph with critical path highlighted (★)
- **DAG Dependencies** — Dataset impact view: what upstream DAGs produce, what downstream DAGs consume
- **Pools** — Slot utilization bars + pool starvation / contention alerts
- **Health** — Scheduler and metadb status
- **Import Errors** — DAG parse errors with timestamps
- **SLA Miss Tracker** — Running DAGs that have exceeded their P95 duration
- **Resource Timeline** — 24-hour ASCII heatmap of pool slot usage with top consumer DAGs
- **XCom Viewer** — XCom key/value inspector for a task instance
- **Watchlist** — Bookmarked DAGs with status, duration drift, and success rate

### Analytics & Diagnostics
- **Run metrics panel** — Success rate, avg/P95 duration, failure streak, sparkline trend
- **Box plot distribution** — `[──├─●──┤──]` showing p50/p75/p95 over last 50 runs
- **Failure heatmap** — 7×24 grid (days × hours) showing when failures cluster
- **Queue latency column** — Time from task queued to task started (identifies worker saturation)
- **SLA miss column** — `⚠ SLA` indicator on task instances that breached their SLA
- **Task log snippet** — Last 30 lines of task log inline, no browser needed
- **Critical path** — Longest dependency chain highlighted in DAG graph

### Interaction
- **Live filter** — `/` to filter by DAG ID with live results
- **Auto-refresh (watch mode)** — `w` to toggle live polling; `[LIVE]` indicator in footer
- **Bookmarks** — `b` to bookmark/unbookmark a DAG; persisted to config
- **Command palette** — `:` for quick navigation and commands
- **Strictly read-only** — Safe to point at production; no writes, no triggers

## Installation

```bash
pip install terminair
```

Or run directly:

```bash
python3 -m terminair --url http://localhost:8080 --user admin --password admin
```

## Quick Start

**Requires a running Airflow instance.**

```bash
# Recommended: set password via env var
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin

# Named connection from config
python3 -m terminair --ctx production
```

## Authentication

Terminair supports three authentication methods:

### Basic Auth (username/password)

```bash
# Option 1: Environment variable (recommended — avoids shell history)
export TERMINAIR_PASSWORD=admin
python3 -m terminair --url http://localhost:8080 --user admin

# Option 2: Interactive prompt (password hidden)
python3 -m terminair --url http://localhost:8080 --user admin
# → Password: ********

# Option 3: CLI argument (visible in process list — use only for local dev)
python3 -m terminair --url http://localhost:8080 --user admin --password admin
```

### Token Auth

Use a config file with an environment variable reference for the token:

```yaml
# ~/.terminair/config.yaml
connections:
  production:
    url: https://airflow.company.com
    auth:
      type: token
      token: ${AIRFLOW_PROD_TOKEN}
```

Then:
```bash
export AIRFLOW_PROD_TOKEN=your-bearer-token
python3 -m terminair --ctx production
```

### Airflow API Setup

Terminair requires the Airflow REST API to be enabled. For Airflow 2.x:

1. Ensure `api` is in your `airflow.cfg`:
   ```ini
   [api]
   auth_backends = airflow.api.auth.backend.basic_auth
   ```

2. For **MWAA** (AWS Managed Airflow): Use a web login token — Terminair's token auth mode works with the session token from the MWAA CLI.

3. For **Cloud Composer** (GCP): Use `gcloud` to generate an access token:
   ```bash
   export AIRFLOW_PROD_TOKEN=$(gcloud auth print-access-token)
   python3 -m terminair --ctx production
   ```

4. For **Astronomer**: Use the Astronomer API token from the Astro CLI.

> **Security note:** Avoid passing passwords as CLI arguments in shared environments — they are visible in `ps` output and shell history. Use `TERMINAIR_PASSWORD` or interactive prompt instead.

## Layout

```
 Connection: localhost:8080    <1> DAGs  <2> Recent  <3> Pools  <4> Health  <5> Errors  <6> SLA  <7> Timeline
 User:       admin             <enter> Drill  <esc> Back  </> Filter  <w> Watch  <b> Bookmark
 Terminair:    v0.1.0            <g> Graph  <h> History  <d> Deps  <0> Watchlist  <:> Cmd  <q> Quit
╭─ dags(5)[0] ───────────────────────────────────────────────────────────────────────╮
│ DAG ID↑    Owner    Schedule    State     Last Run    Duration    Next Run    Active │
│ ★ my_dag   airflow  @daily      active    2024-01-01  2m 10s      tomorrow    yes    │
│ ...                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────╯
  <dags>  [LIVE]
```

## Keybindings

| Key | Action |
|-----|--------|
| `1` | DAGs overview |
| `2` | Recent activity |
| `3` | Pools |
| `4` | Health |
| `5` | Import errors |
| `6` | SLA Miss Tracker |
| `7` | Resource Timeline (24h pool usage) |
| `0` | Watchlist (bookmarked DAGs) |
| `Enter` | Drill into selected DAG |
| `Esc` | Back / clear filter |
| `/` | Live filter by DAG ID |
| `w` | Toggle auto-refresh (LIVE mode) |
| `b` | Bookmark / unbookmark selected DAG |
| `g` | DAG dependency graph |
| `h` | Task history (cross-run pattern) |
| `d` | DAG dependency impact view |
| `x` | XCom viewer (from Task Instances) |
| `l` | Task log snippet (from Task Instances) |
| `:` | Command palette |
| `q` | Quit |

## Commands

```
:dag daily_orders     Jump to DAG
:pools                Switch to pools
:health               Switch to health
:ctx production       Switch connection
:filter state=failed  Filter view
:export json          Export current view
```

## Configuration

Config lives at `~/.terminair/config.yaml`:

```yaml
connections:
  default:
    url: http://localhost:8080
    auth:
      type: basic
      username: admin
      password: admin
  production:
    url: https://airflow.company.com
    auth:
      type: token
      token: ${AIRFLOW_PROD_TOKEN}

settings:
  default_connection: default
  refresh_interval: 5        # seconds between auto-refresh ticks
  show_sensitive: false      # default: hide XCom value previews
  watchlist:
    - my_critical_dag
    - daily_revenue_pipeline
```

## Design Principles

1. **Read-only first** — No triggers, clears, or state changes. Safe for production.
2. **Debugging focused** — Every screen answers a specific operational question.
3. **Sub-second navigation** — Background polling, cached state.
4. **Zero infrastructure** — Connects via Airflow REST API, no agents or sidecars.

## Requirements

- Python 3.11+
- Airflow 2.0+ with REST API enabled

## Security & Privacy Defaults

- Read-only API client: no trigger/clear/mutation methods are implemented.
- Password and token values should be provided via environment variables or interactive prompt.
- Debug logging is disabled by default. To opt in: `TERMINAIR_DEBUG=1`.
- XCom value previews are redacted by default. To show values for a trusted session:
  - set `settings.show_sensitive: true` in config, or
  - run with `TERMINAIR_SHOW_SENSITIVE=1`.

## Testing

```bash
python3 -m pytest terminair/tests/ -v
```

## License

MIT
