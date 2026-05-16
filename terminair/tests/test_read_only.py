"""Tests to enforce read-only contract for AirflowBridge."""

from __future__ import annotations

import inspect


def test_airflow_bridge_has_no_write_methods():
    """AirflowBridge must expose zero write methods (post, put, delete, patch)."""
    from terminair.dbt.airflow_bridge import AirflowBridge

    members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
    write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
    assert not write_methods, f"Found write methods on AirflowBridge: {write_methods}"
