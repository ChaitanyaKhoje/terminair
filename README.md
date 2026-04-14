# AirTerm

A k9s-style TUI for Apache Airflow — read-only terminal interface for monitoring and debugging DAGs.

## Features

- **Strictly read-only** — Safe to point at production from day one
- **k9s-style layout** — Inline key hints in header, table with count/filter indicator
- **DAGs overview** — All DAGs with status, schedule, active state
- **Run history** — Per-DAG metrics (success rate, p95 duration, sparkline)
- **Task instances** — With error summary column
- **Task history** — Cross-run pass/fail pattern to identify flaky tasks
- **Pools** — Utilization bars
- **Health** — Scheduler and metadb status
- **Live filter** — `/` to filter by DAG ID with live results
- **Multiple clusters** — Switch between dev/staging/production

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
python3 -m airterm --url http://localhost:8080 --user admin --password admin
python3 -m airterm --ctx production
```

## Layout

```
 Connection: localhost:8080    <1> DAGs  <2> Recent  <3> Pools  <4> Health  <5> Errors
 User:       admin             <enter> Drill  <esc> Back  </> Filter  <r> Refresh
 AirTerm:    v0.1.0            <g> Graph  <h> History  <:> Command  <q> Quit
╭─ dags(5)[0] ───────────────────────────────────────────────────────────────────────╮
│ DAG ID↑    Owner    Schedule    State     Last Run    Duration    Next Run    Active │
│ ...                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────╯
  <dags>
```

When a filter is active:
```
╭─ dags(2/5)[0] [/etl] ──────────────────────────────────────────────────────────────╮
  <dags>  filter: /etl  <esc> clear
```

## Keybindings

| Key | Action |
|-----|--------|
| `1` | DAGs overview |
| `2` | Recent activity |
| `3` | Pools |
| `4` | Health |
| `5` | Import errors |
| `Enter` | Drill into selected item |
| `Esc` | Back / clear filter |
| `/` | Live filter by DAG ID |
| `:` | Command palette |
| `r` | Refresh |
| `h` | Task history |
| `g` | DAG graph |
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

## Design Principles

1. **Read-only first** — No triggers, clears, or state changes
2. **Debugging focused** — Every screen answers a specific operational question
3. **Sub-second navigation** — Background polling, cached state
4. **Zero infrastructure** — Connects via Airflow REST API

## Testing

```bash
python3 -m pytest airterm/tests/ -v
```

## Requirements

- Python 3.9+
- Airflow 2.0+ REST API

## License

MIT
