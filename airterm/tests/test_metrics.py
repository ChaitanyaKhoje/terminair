"""Tests for metrics engine."""

from datetime import datetime

import pytest

from airterm.metrics.aggregations import (
    compute_duration_stats,
    compute_streak,
    compute_success_rate,
)
from airterm.metrics.error_extract import extract_error
from airterm.metrics.sparkline import compute_sparkline, render_pattern


@pytest.fixture
def sample_runs():
    from airterm.api.models import DagRun, DagRunState

    base = datetime(2026, 4, 13)
    return [
        DagRun(
            dag_run_id=f"run_{i}",
            dag_id="test",
            execution_date=base,
            state=DagRunState.SUCCESS if i % 2 == 0 else DagRunState.FAILED,
            run_type="scheduled",
            external_trigger=False,
            start_date=base,
            end_date=base,
        )
        for i in range(10)
    ]


def test_compute_streak(sample_runs):
    streak = compute_streak(sample_runs)
    assert streak["type"] in ["success", "failed"]
    assert streak["count"] >= 1


def test_compute_success_rate(sample_runs):
    rate = compute_success_rate(sample_runs)
    assert rate == 0.5


def test_compute_duration_stats():
    from airterm.api.models import DagRun, DagRunState

    base = datetime(2026, 4, 13)
    runs = [
        DagRun(
            dag_run_id=f"run_{i}",
            dag_id="test",
            execution_date=base,
            state=DagRunState.SUCCESS,
            run_type="scheduled",
            external_trigger=False,
            start_date=base,
            end_date=base,
        )
        for i in range(5)
    ]
    stats = compute_duration_stats(runs)
    assert stats["avg"] >= 0


def test_compute_sparkline():
    durations = [100, 150, 200, 120, 180, 110]
    sparkline = compute_sparkline(durations)
    assert len(sparkline) == 6


def test_render_pattern():
    states = ["success", "success", "failed", "success"]
    pattern = render_pattern(states)
    assert pattern == "✓ ✓ ✗ ✓"


def test_extract_error_with_traceback():
    log = """
    [2026-04-13 05:12:33] INFO - Starting extract
    [2026-04-13 05:12:45] INFO - Fetched 5000 rows
    Traceback (most recent call last):
      File "/opt/airflow/dags/daily_orders.py", line 42, in extract
        df = pd.read_sql(query, conn)
    sqlalchemy.exc.OperationalError: connection refused
    """
    error = extract_error(log)
    assert "OperationalError" in error["summary"] or "connection refused" in error["summary"]


def test_extract_error_no_traceback():
    log = "Task exited with return code 1\n"
    error = extract_error(log)
    assert "return code 1" in error["summary"]
