# AirTerm

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
pip install airterm
```

Or run directly:

```bash
python3 -m airterm --url http://localhost:8080 --user admin --password admin
```

## Quick Start

**Requires a running Airflow instance.**

```bash
# Basic auth
python3 -m airterm --url http://localhost:8080 --user admin --password admin

# Named connection from config
python3 -m airterm --ctx production
```

## Layout

```
 Connection: localhost:8080    <1> DAGs  <2> Recent  <3> Pools  <4> Health  <5> Errors  <6> SLA  <7> Timeline
 User:       admin             <enter> Drill  <esc> Back  </> Filter  <w> Watch  <b> Bookmark
 AirTerm:    v0.1.0            <g> Graph  <h> History  <d> Deps  <0> Watchlist  <:> Cmd  <q> Quit
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

Config lives at `~/.airterm/config.yaml`:

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

- Python 3.9+
- Airflow 2.0+ with REST API enabled

## Testing

```bash
python3 -m pytest airterm/tests/ -v
```

## License

MIT
