"""Tests for ArtifactReader — run_results.json parsing with graceful missing-file handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from terminair.dbt.artifacts import ArtifactReader

FIXTURES = Path(__file__).parent.parent.parent / "dbt" / "fixtures"


def test_artifact_reader_loads_all_results():
    """ArtifactReader indexes all 10 results from run_results.json."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    assert len(ar.get_all_node_ids()) == 10


def test_get_result_returns_dict_for_known_node():
    """get_result() returns the result dict for a known node_id."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    result = ar.get_result("model.my_project.stg_orders")
    assert result is not None
    assert result["status"] == "success"


def test_get_result_returns_none_for_unknown():
    """get_result() returns None (not KeyError) for an unknown node_id."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    assert ar.get_result("model.my_project.does_not_exist") is None


def test_missing_results_file_raises_file_not_found(tmp_path):
    """ArtifactReader raises FileNotFoundError when results_path missing."""
    with pytest.raises(FileNotFoundError, match="run_results.json"):
        ArtifactReader(tmp_path / "run_results.json")


def test_rows_affected_for_success_node():
    """get_rows_affected() returns the integer row count for a success node."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    rows = ar.get_rows_affected("model.my_project.stg_orders")
    assert rows == 15000


def test_rows_affected_none_for_running():
    """get_rows_affected() returns None for a running node."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    rows = ar.get_rows_affected("model.my_project.fct_revenue_daily")
    assert rows is None


def test_rows_affected_none_for_unknown_node():
    """get_rows_affected() returns None when node_id is not in results."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    assert ar.get_rows_affected("nonexistent.node") is None


def test_get_previous_result_none_when_no_previous():
    """get_previous_result() returns None when previous_path is not provided."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    assert ar.get_previous_result("model.my_project.stg_orders") is None


def test_get_previous_result_none_when_file_missing(tmp_path):
    """get_previous_result() returns None when previous file does not exist."""
    ar = ArtifactReader(
        FIXTURES / "run_results.json",
        previous_path=tmp_path / "missing.json",
    )
    assert ar.get_previous_result("model.my_project.stg_orders") is None


def test_get_previous_result_with_previous_file():
    """get_previous_result() returns previous result when previous_path is valid."""
    ar = ArtifactReader(
        FIXTURES / "run_results.json",
        previous_path=FIXTURES / "run_results_previous.json",
    )
    prev = ar.get_previous_result("model.my_project.stg_orders")
    assert prev is not None
    assert prev["adapter_response"]["rows_affected"] == 20000


def test_get_execution_time():
    """get_execution_time() returns a float for a completed node."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    exec_time = ar.get_execution_time("model.my_project.stg_orders")
    assert exec_time is not None
    assert isinstance(exec_time, float)


def test_get_execution_time_none_for_unknown():
    """get_execution_time() returns None for an unknown node_id."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    assert ar.get_execution_time("nonexistent.node") is None


def test_get_timing_returns_tuple():
    """get_timing() returns a (started_at, completed_at) tuple."""
    ar = ArtifactReader(FIXTURES / "run_results.json")
    started, completed = ar.get_timing("model.my_project.stg_orders")
    assert isinstance(started, (str, type(None)))
    assert isinstance(completed, (str, type(None)))
