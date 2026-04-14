"""DAG Detail screen with run history and metrics panel."""

from datetime import datetime
from statistics import quantiles

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Static


def _box_plot(durations: list[float]) -> str:
    if len(durations) < 2:
        return "-- not enough data --"
    try:
        pcts = quantiles(sorted(durations), n=4)
    except ValueError:
        return "-- not enough data --"
    mn, p25, p50, p75, mx = min(durations), pcts[0], pcts[1], pcts[2], max(durations)
    rng = mx - mn if mx != mn else 1

    def pos(v: float) -> int:
        return int(((v - mn) / rng) * 18) + 1

    bar = [" "] * 20
    for i in range(pos(mn), pos(mx) + 1):
        if 0 <= i < 20:
            bar[i] = "─"
    for p, ch in [(pos(p25), "├"), (pos(p50), "●"), (pos(p75), "┤")]:
        if 0 <= p < 20:
            bar[p] = ch
    return f"[{''.join(bar)}] p50:{p50:.0f}s p75:{p75:.0f}s p95:{sorted(durations)[int(len(durations)*0.95)]:.0f}s"


def _failure_heatmap(runs: list) -> str:
    """7-row (days) × 24-col (hours) heatmap of failures."""
    grid: dict[tuple[int, int], int] = {}
    total: dict[tuple[int, int], int] = {}

    for run in runs:
        if not run.start_date:
            continue
        dow = run.start_date.weekday()  # 0=Mon
        hour = run.start_date.hour
        total[(dow, hour)] = total.get((dow, hour), 0) + 1
        if run.state and run.state.value == "failed":
            grid[(dow, hour)] = grid.get((dow, hour), 0) + 1

    if not total:
        return ""

    days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    shades = " ░▒▓█"
    lines = ["     " + "".join(f"{h:02d}" if h % 4 == 0 else "  " for h in range(24))]
    for d in range(7):
        row = days[d] + "  "
        for h in range(24):
            t = total.get((d, h), 0)
            f = grid.get((d, h), 0)
            if t == 0:
                row += "  "
            else:
                ratio = f / t
                idx = min(int(ratio * 4), 4)
                row += shades[idx] * 2
        lines.append(row)
    return "\n".join(lines)


class DagDetailScreen(Screen):
    CSS = """
    DagDetailScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 16;
    }

    #run-table {
        height: 100%;
    }

    #metrics-panel {
        height: 100%;
        background: $panel;
        padding: 1 2;
        overflow-y: auto;
    }

    .metric-label {
        color: $text-muted;
    }

    .metric-value {
        color: $text;
    }

    .sparkline {
        color: $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(id="run-table")
        yield Static("", id="metrics-panel")

    def on_mount(self) -> None:
        table = self.query_one("#run-table")
        table.add_columns(
            "Run ID",
            "State",
            "Type",
            "Execution",
            "Duration",
            "vs Avg",
            "Error",
        )

    def update_runs(self, runs: list, avg_duration: float = 0.0):
        table = self.query_one("#run-table")
        table.clear()
        for run in runs:
            duration = ""
            vs_avg = ""
            if run.start_date and run.end_date:
                delta = run.end_date - run.start_date
                seconds = delta.total_seconds()
                duration = f"{int(seconds // 60)}m {int(seconds % 60)}s"
                if avg_duration > 0:
                    drift = ((seconds - avg_duration) / avg_duration) * 100
                    sign = "+" if drift > 0 else ""
                    vs_avg = f"{sign}{drift:.0f}%"

            error = ""
            if run.state.value == "failed":
                error = run.dag_run_id[:30]

            table.add_row(
                run.dag_run_id[:30],
                run.state.value if run.state else "",
                run.run_type,
                str(run.execution_date)[:16],
                duration,
                vs_avg,
                error,
            )

    def update_metrics(
        self,
        dag_id: str,
        schedule: str,
        owner: str,
        total_runs: int,
        success_count: int,
        failure_count: int,
        success_rate: float,
        avg_duration: float,
        p95_duration: float,
        streak_type: str,
        streak_count: int,
        sparkline: str,
        last_failure: str,
        runs: list = None,
    ):
        durations = []
        if runs:
            for run in runs:
                if run.start_date and run.end_date:
                    durations.append((run.end_date - run.start_date).total_seconds())

        box = _box_plot(durations) if durations else "-- no data --"
        heatmap = _failure_heatmap(runs) if runs else ""

        heatmap_section = f"\nFailure Heatmap (darker = more failures):\n{heatmap}" if heatmap else ""

        self.query_one("#metrics-panel").update(
            f"""DAG: {dag_id} | Schedule: {schedule} | Owner: {owner}
─────────────────────────────────────────────
Runs (last 50): {total_runs} total | {success_count} success | {failure_count} failed
Success Rate:   {success_rate:.1f}%
Avg Duration:   {int(avg_duration // 60)}m {int(avg_duration % 60)}s
P95 Duration:   {int(p95_duration // 60)}m {int(p95_duration % 60)}s
Last Failure:   {last_failure or "none"}
Streak:         {streak_count} ({streak_type})
Trend:          {sparkline}
Distribution:   {box}{heatmap_section}
"""
        )
