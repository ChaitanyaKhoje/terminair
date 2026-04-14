"""Metrics aggregation functions."""

from datetime import datetime, timedelta
from typing import Optional

from airterm.api.models import DagRun, DagRunState


def compute_streak(runs: list[DagRun]) -> dict:
    if not runs:
        return {"type": "none", "count": 0}

    terminal_states = {"success", "failed"}
    streak_type = None
    streak_count = 0

    for run in runs:
        if run.state not in terminal_states:
            break
        current_type = run.state.value
        if streak_type is None:
            streak_type = current_type
            streak_count = 1
        elif current_type == streak_type:
            streak_count += 1
        else:
            break

    return {"type": streak_type or "none", "count": streak_count}


def compute_success_rate(runs: list[DagRun]) -> float:
    if not runs:
        return 0.0
    success_count = sum(1 for r in runs if r.state == DagRunState.SUCCESS)
    return success_count / len(runs)


def compute_duration_stats(runs: list[DagRun]) -> dict:
    durations = []
    for run in runs:
        if run.start_date and run.end_date:
            delta = run.end_date - run.start_date
            durations.append(delta.total_seconds())

    if not durations:
        return {
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "max": 0.0,
        }

    sorted_durations = sorted(durations)
    count = len(sorted_durations)

    return {
        "avg": sum(durations) / count,
        "p50": sorted_durations[int(count * 0.5)],
        "p95": sorted_durations[int(count * 0.95)] if count > 1 else sorted_durations[0],
        "max": sorted_durations[-1],
    }


def compute_duration_drift(last_duration: float, avg_duration: float) -> float:
    if avg_duration == 0:
        return 0.0
    return ((last_duration - avg_duration) / avg_duration) * 100


def find_last_failure(runs: list[DagRun]) -> Optional[DagRun]:
    for run in runs:
        if run.state == DagRunState.FAILED:
            return run
    return None
