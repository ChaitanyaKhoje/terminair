"""Tests for AirflowBridge — verifies GET-only constraint, fuzzy match, and error handling."""
from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Import tests — must succeed before any instantiation tests
# ---------------------------------------------------------------------------

def test_airflow_bridge_importable():
    """AirflowBridge must be importable with no side effects."""
    from terminair.dbt.airflow_bridge import AirflowBridge, AirflowBridgeError  # noqa: F401

    assert AirflowBridge is not None
    assert AirflowBridgeError is not None


def test_airflow_bridge_error_is_exception():
    from terminair.dbt.airflow_bridge import AirflowBridgeError

    assert issubclass(AirflowBridgeError, Exception)


# ---------------------------------------------------------------------------
# GET-only constraint
# ---------------------------------------------------------------------------

def test_no_write_methods_on_airflow_bridge():
    """AirflowBridge must have zero POST/PUT/DELETE/PATCH methods."""
    from terminair.dbt.airflow_bridge import AirflowBridge

    members = dict(inspect.getmembers(AirflowBridge, predicate=inspect.isfunction))
    write_methods = [m for m in members if m in ("post", "put", "delete", "patch")]
    assert not write_methods, f"Found write methods: {write_methods}"


def test_no_write_calls_in_source():
    """Source file must not contain any self._client.post/put/delete/patch calls."""
    import pathlib

    source = pathlib.Path("terminair/dbt/airflow_bridge.py").read_text()
    for verb in ("post", "put", "delete", "patch"):
        assert f"self._client.{verb}" not in source, (
            f"Found forbidden call 'self._client.{verb}' in airflow_bridge.py"
        )


# ---------------------------------------------------------------------------
# close() method
# ---------------------------------------------------------------------------

def test_close_method_exists():
    from terminair.dbt.airflow_bridge import AirflowBridge

    assert hasattr(AirflowBridge, "close"), "close() method must exist"
    assert inspect.iscoroutinefunction(AirflowBridge.close), "close() must be async"


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def test_fuzzy_match_substring():
    """Substring matching: 'run_fct_revenue_daily' → 'fct_revenue_daily'."""
    from terminair.dbt.airflow_bridge import _fuzzy_match

    result = _fuzzy_match("run_fct_revenue_daily", ["fct_revenue_daily", "stg_orders"])
    assert result == "fct_revenue_daily"


def test_fuzzy_match_exact():
    from terminair.dbt.airflow_bridge import _fuzzy_match

    result = _fuzzy_match("stg_orders", ["fct_revenue_daily", "stg_orders"])
    assert result == "stg_orders"


def test_fuzzy_match_no_match_returns_none():
    from terminair.dbt.airflow_bridge import _fuzzy_match

    result = _fuzzy_match("nonexistent_xyz_abc_qqq", ["fct_revenue_daily", "stg_orders"])
    assert result is None


def test_fuzzy_match_close_enough():
    """difflib fallback: 'fct_revnue_daily' (typo) should still match."""
    from terminair.dbt.airflow_bridge import _fuzzy_match

    result = _fuzzy_match("fct_revnue_daily", ["fct_revenue_daily", "stg_orders"])
    assert result == "fct_revenue_daily"


# ---------------------------------------------------------------------------
# Instantiation (no HTTP call)
# ---------------------------------------------------------------------------

def test_instantiation_no_http_call():
    """__init__ must not make any HTTP requests."""
    from terminair.config import Connection, ConnectionAuthBasic
    from terminair.dbt.airflow_bridge import AirflowBridge

    conn = Connection(
        url="http://localhost:9999",
        auth=ConnectionAuthBasic(username="u", password="p"),
    )
    bridge = AirflowBridge(conn)
    # If no exception raised, no HTTP call was made (unreachable port, no timeout)
    assert bridge is not None


@pytest.mark.asyncio
async def test_close_calls_aclose():
    """close() must call self._client.aclose()."""
    from unittest.mock import AsyncMock, patch

    from terminair.config import Connection, ConnectionAuthBasic
    from terminair.dbt.airflow_bridge import AirflowBridge

    conn = Connection(
        url="http://localhost:9999",
        auth=ConnectionAuthBasic(username="u", password="p"),
    )
    bridge = AirflowBridge(conn)
    bridge._client.aclose = AsyncMock()
    await bridge.close()
    bridge._client.aclose.assert_called_once()
