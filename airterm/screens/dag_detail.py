"""DAG Detail screen with run history and metrics panel.

This file contains the DAG detail screen and the failure-heatmap rendering
helpers. The heatmap was redesigned to use color-intensity backgrounds with a
Unicode block fallback for monochrome terminals.
"""

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
    return f"[{''.join(bar)}] p50:{p50:.0f}s p75:{p75:.0f}s p95:{sorted(durations)[int(len(durations) * 0.95)]:.0f}s"


# --- Failure Heatmap Helper Constants and Functions (2026 Redesign) ---

# Bucket thresholds for failure count→color/shade mapping (inclusive upper bounds, see spec)
FAILURE_BUCKET_1_MAX = 1  # 0–1 failures → green/░
FAILURE_BUCKET_2_MAX = 5  # 2–5 failures → yellow/▒
FAILURE_BUCKET_3_MAX = 10  # 6–10 failures → orange/▓
# 11+ failures → red/█


def failure_count_to_style(failure_count: int) -> str:
    """
    Map a failure count to a Textual-compatible background color style string for heatmaps.
    Buckets (per spec):
        0–1   → 'on green'
        2–5   → 'on yellow'
        6–10  → 'on orange'
        11+   → 'on red'
    Defensive: Any negative value maps to the first bucket (green).
    """
    try:
        c = int(failure_count)
    except Exception:
        c = 0
    if c <= FAILURE_BUCKET_1_MAX:
        return "on green"
    elif c <= FAILURE_BUCKET_2_MAX:
        return "on yellow"
    elif c <= FAILURE_BUCKET_3_MAX:
        return "on orange"
    else:
        return "on red"


def failure_count_to_block_char(failure_count: int) -> str:
    """
    Map a failure count to a Unicode block character representing intensity for monochrome heatmaps.
    Buckets (per spec):
        0–1   → '░' (U+2591: light shade)
        2–5   → '▒' (U+2592: medium shade)
        6–10  → '▓' (U+2593: dark shade)
        11+   → '█' (U+2588: full block)
    Defensive: Any negative value maps to '░'.
    """
    try:
        c = int(failure_count)
    except Exception:
        c = 0
    if c <= FAILURE_BUCKET_1_MAX:
        return "░"
    elif c <= FAILURE_BUCKET_2_MAX:
        return "▒"
    elif c <= FAILURE_BUCKET_3_MAX:
        return "▓"
    else:
        return "█"


def _failure_heatmap(runs: list, color_enabled: bool = True) -> tuple[str, str]:
    """Render a 7×24 failure heatmap and return (heatmap_str, legend_str).

    The grid layout: 7 rows (Mon..Sun) and 24 columns (hours). When color_enabled
    is True, each non-empty cell is rendered with a background color and shows
    the numeric count only when >= 2. When False, a Unicode block is used.
    """
    grid: dict[tuple[int, int], int] = {}
    total: dict[tuple[int, int], int] = {}

    for run in runs:
        if not getattr(run, "start_date", None):
            continue
        dow = run.start_date.weekday()  # 0=Mon
        hour = run.start_date.hour
        total[(dow, hour)] = total.get((dow, hour), 0) + 1
        if getattr(run, "state", None) and run.state.value == "failed":
            grid[(dow, hour)] = grid.get((dow, hour), 0) + 1

    if not total:
        return "", ""

    days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    # Header: show hour labels every 4 columns for compactness
    lines = ["     " + "".join(f"{h:02d}" if h % 4 == 0 else "  " for h in range(24))]

    for d in range(7):
        row = days[d] + "  "
        for h in range(24):
            t = total.get((d, h), 0)
            f = grid.get((d, h), 0)
            if t == 0:
                row += "  "
            else:
                if color_enabled:
                    style = failure_count_to_style(f)
                    content = f"{f}" if f >= 2 else ""
                    content = f"{content:>2}"
                    row += f"[{style}]{content}[/]"
                else:
                    block = failure_count_to_block_char(f)
                    row += block * 2
        lines.append(row)

    heatmap_str = "\n".join(lines)
    if color_enabled:
        legend_str = "Heatmap: green (0–1) → yellow (2–5) → orange (6–10) → red (11+)"
    else:
        legend_str = "Heatmap: ░ (0–1) → ▒ (2–5) → ▓ (6–10) → █ (11+)"

    return heatmap_str, legend_str


class DagDetailScreen(Screen):
    CSS = """
    DagDetailScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 16;
    }

    # ... styles unchanged ...
    # keeping original CSS from previous implementation

    # run-table and metrics-panel are used in compose()
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
            "Drift",
            "Error",
        )

    def update_runs(self, runs: list, avg_duration: float = 0.0):
        table = self.query_one("#run-table")
        table.clear()
        state_colors = {
            "success": "green",
            "failed": "red",
            "running": "yellow",
            "queued": "cyan",
        }
        for run in runs:
            duration = ""
            drift = ""
            if run.start_date and run.end_date:
                delta = run.end_date - run.start_date
                seconds = delta.total_seconds()
                duration = f"{int(seconds // 60)}m {int(seconds % 60)}s"
                if avg_duration > 0:
                    pct = ((seconds - avg_duration) / avg_duration) * 100
                    sign = "+" if pct > 0 else ""
                    drift_color = "red" if pct > 20 else ("yellow" if pct > 0 else "green")
                    drift = f"[{drift_color}]{sign}{pct:.0f}%[/{drift_color}]"

            state_val = run.state.value if run.state else ""
            state_color = state_colors.get(state_val, "white")
            colored_state = f"[{state_color}]{state_val}[/{state_color}]"

            error = ""
            if state_val == "failed":
                error = f"[red]{run.dag_run_id[:30]}[/red]"

            table.add_row(
                run.dag_run_id[:30],
                colored_state,
                f"[dim]{run.run_type}[/dim]",
                str(run.execution_date)[:16],
                duration,
                drift,
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
        heatmap_str, legend_str = _failure_heatmap(runs, color_enabled=True) if runs else ("", "")

        heatmap_section = (
            f"\nFailure Heatmap (color = failures — see legend):\n{legend_str}\n{heatmap_str}"
            if heatmap_str
            else ""
        )

        sr_color = "green" if success_rate >= 90 else ("yellow" if success_rate >= 70 else "red")
        streak_color = (
            "green"
            if streak_type == "success"
            else ("red" if streak_type == "failure" else "white")
        )
        failure_color = "red" if failure_count > 0 else "green"
        last_failure_str = f"[red]{last_failure}[/red]" if last_failure else "[green]none[/green]"

        self.query_one("#metrics-panel").update(
            f"[bold cyan]{dag_id}[/bold cyan]  "
            f"[dim]schedule:[/dim] [yellow]{schedule}[/yellow]  "
            f"[dim]owner:[/dim] [white]{owner}[/white]\n"
            f"─────────────────────────────────────────────\n"
            f"[dim]Runs (last 50):[/dim] {total_runs} total  "
            f"[green]{success_count} success[/green]  "
            f"[{failure_color}]{failure_count} failed[/{failure_color}]\n"
            f"[dim]Success Rate:[/dim]   [{sr_color}]{success_rate:.1f}%[/{sr_color}]\n"
            f"[dim]Avg Duration:[/dim]   [white]{int(avg_duration // 60)}m {int(avg_duration % 60)}s[/white]\n"
            f"[dim]P95 Duration:[/dim]   [yellow]{int(p95_duration // 60)}m {int(p95_duration % 60)}s[/yellow]\n"
            f"[dim]Last Failure:[/dim]   {last_failure_str}\n"
            f"[dim]Streak:[/dim]         [{streak_color}]{streak_count} {streak_type}[/{streak_color}]\n"
            f"[dim]Trend:[/dim]          [cyan]{sparkline}[/cyan]\n"
            f"[dim]Distribution:[/dim]   {box}{heatmap_section}\n"
        )
