from datetime import datetime

from airterm.screens.dag_detail import (
    failure_count_to_style,
    failure_count_to_block_char,
    _failure_heatmap,
)
from airterm.api.models import DagRun, DagRunState


def make_run(day: int, hour: int, failed: bool) -> DagRun:
    base = datetime(2026, 4, 13)
    # set start_date with weekday matching 'day' by offsetting days
    start = base
    # move forward `day` days
    start = start.replace(day=base.day + day)
    start = start.replace(hour=hour)
    state = DagRunState.FAILED if failed else DagRunState.SUCCESS
    return DagRun(
        dag_run_id=f"r_{day}_{hour}_{'F' if failed else 'S'}",
        dag_id="test",
        execution_date=start,
        start_date=start,
        end_date=start,
        state=state,
        run_type="scheduled",
        external_trigger=False,
    )


def test_failure_count_to_style_and_block():
    # style mapping
    assert failure_count_to_style(-1) == "on green"
    assert failure_count_to_style(0) == "on green"
    assert failure_count_to_style(1) == "on green"
    assert failure_count_to_style(2) == "on yellow"
    assert failure_count_to_style(5) == "on yellow"
    assert failure_count_to_style(6).startswith("on")
    assert failure_count_to_style(10).startswith("on")
    assert failure_count_to_style(11) == "on red"

    # block mapping
    assert failure_count_to_block_char(-3) == "░"
    assert failure_count_to_block_char(0) == "░"
    assert failure_count_to_block_char(1) == "░"
    assert failure_count_to_block_char(2) == "▒"
    assert failure_count_to_block_char(5) == "▒"
    assert failure_count_to_block_char(6) == "▓"
    assert failure_count_to_block_char(10) == "▓"
    assert failure_count_to_block_char(11) == "█"


def test_failure_heatmap_rendering_modes():
    # Build runs to produce various buckets
    runs = []
    # Day 0, hour 0: two runs, one failed -> f=1 (green)
    runs.append(make_run(0, 0, False))
    runs.append(make_run(0, 0, True))

    # Day 0, hour 1: three runs, two failed -> f=2 (yellow)
    runs.append(make_run(0, 1, True))
    runs.append(make_run(0, 1, True))
    runs.append(make_run(0, 1, False))

    # Day 1, hour 2: 12 failed runs -> f=12 (red)
    for i in range(12):
        runs.append(make_run(1, 2, True))

    heatmap_str_color, legend_color = _failure_heatmap(runs, color_enabled=True)
    assert "green (0–1)" in legend_color
    # color markup should appear (on yellow/on red or hex)
    assert (
        "on yellow" in heatmap_str_color
        or "on #" in heatmap_str_color
        or "on red" in heatmap_str_color
    )
    # numeric overlay for f=2 should be present (" 2" within markup)
    assert "2" in heatmap_str_color

    heatmap_str_mono, legend_mono = _failure_heatmap(runs, color_enabled=False)
    assert "░ (0–1)" in legend_mono
    # monochrome should contain block chars
    assert "░" in heatmap_str_mono or "▒" in heatmap_str_mono or "█" in heatmap_str_mono
