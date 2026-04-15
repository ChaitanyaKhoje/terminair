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
        6–10  → 'on orange' (use 'on darkorange' if 'orange' is unavailable)
        11+   → 'on red'
    Defensive: Any negative value maps to the first bucket (green).

    Args:
        failure_count (int): Number of failures for a cell/bucket.

    Returns:
        str: Textual style string like 'on green', 'on yellow', etc.
    """
    if failure_count <= FAILURE_BUCKET_1_MAX:
        return "on green"
    elif failure_count <= FAILURE_BUCKET_2_MAX:
        return "on yellow"
    elif failure_count <= FAILURE_BUCKET_3_MAX:
        # Textual supports 'orange' as a style, fallback to 'darkorange' if not recognized in theme
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

    Args:
        failure_count (int): Number of failures for a cell/bucket.
    Returns:
        str: Appropriate Unicode shade character.
    """
    if failure_count <= FAILURE_BUCKET_1_MAX:
        return "░"  # light shade
    elif failure_count <= FAILURE_BUCKET_2_MAX:
        return "▒"  # medium shade
    elif failure_count <= FAILURE_BUCKET_3_MAX:
        return "▓"  # dark shade
    else:
        return "█"  # full block


# --- End: Failure Heatmap Helper Functions ---


def _failure_heatmap(runs: list, color_enabled: bool = True) -> tuple[str, str]:
    """Render a 7×24 failure heatmap and return (heatmap_str, legend_str).

    The grid layout matches the prior implementation: 7 rows (Mon..Sun) and 24
    columns (hours). When color_enabled is True, each non-empty cell is rendered
    with a background color (via failure_count_to_style) and shows the numeric
    count only when >= 2 to keep the grid readable. When color_enabled is False,
    a single Unicode block character (from failure_count_to_block_char) is used
    and no numeric overlay is shown.

    Returns:
        (heatmap_str, legend_str) — both strings ready for insertion into the
        metrics panel. If there are no runs, returns ("", "").
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
                    # Show numeric overlay only for counts >= 2; keep 2-char width
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
