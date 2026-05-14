"""Tests for SnowflakeClient — env-var mock, DI fixture_path, and no-mock behaviour."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).parent.parent.parent / "dbt" / "fixtures" / "query_history.json"


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------

def test_snowflake_client_importable():
    """SnowflakeClient must be importable with no side effects."""
    from terminair.dbt.snowflake_client import SnowflakeClient  # noqa: F401

    assert SnowflakeClient is not None


# ---------------------------------------------------------------------------
# No-mock behaviour (TERMINAIR_MOCK_SNOWFLAKE not set)
# ---------------------------------------------------------------------------

def test_no_mock_returns_none(monkeypatch):
    """Without TERMINAIR_MOCK_SNOWFLAKE, get_bytes_scanned returns None."""
    monkeypatch.delenv("TERMINAIR_MOCK_SNOWFLAKE", raising=False)
    # Re-import after env manipulation to pick up env at __init__ time
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient()
    assert sc.get_bytes_scanned("fct_revenue_daily") is None
    assert sc.get_bytes_scanned("stg_orders") is None
    assert sc.get_bytes_scanned("nonexistent_model") is None


# ---------------------------------------------------------------------------
# Mock mode — TERMINAIR_MOCK_SNOWFLAKE=1
# ---------------------------------------------------------------------------

def test_mock_mode_returns_bytes_scanned(monkeypatch):
    """With TERMINAIR_MOCK_SNOWFLAKE=1, returns fixture values."""
    monkeypatch.setenv("TERMINAIR_MOCK_SNOWFLAKE", "1")
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient()
    assert sc.get_bytes_scanned("fct_revenue_daily") == 2147483648


def test_mock_mode_true_string(monkeypatch):
    """TERMINAIR_MOCK_SNOWFLAKE='true' should also activate mock."""
    monkeypatch.setenv("TERMINAIR_MOCK_SNOWFLAKE", "true")
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient()
    assert sc.get_bytes_scanned("fct_revenue_daily") == 2147483648


def test_mock_mode_yes_string(monkeypatch):
    """TERMINAIR_MOCK_SNOWFLAKE='yes' should also activate mock."""
    monkeypatch.setenv("TERMINAIR_MOCK_SNOWFLAKE", "yes")
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient()
    assert sc.get_bytes_scanned("fct_orders") == 1073741824


def test_mock_unknown_model_returns_none(monkeypatch):
    """In mock mode, unknown model names return None."""
    monkeypatch.setenv("TERMINAIR_MOCK_SNOWFLAKE", "1")
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient()
    assert sc.get_bytes_scanned("nonexistent_model_xyz") is None


# ---------------------------------------------------------------------------
# Dependency injection — fixture_path override
# ---------------------------------------------------------------------------

def test_di_fixture_path(monkeypatch):
    """fixture_path kwarg loads from custom path when mock is enabled."""
    monkeypatch.setenv("TERMINAIR_MOCK_SNOWFLAKE", "1")
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient(fixture_path=FIXTURE_PATH)
    assert sc.get_bytes_scanned("mart_platform_usage") == 4294967296


def test_di_fixture_path_no_mock(monkeypatch):
    """fixture_path kwarg without mock env has no effect — returns None."""
    monkeypatch.delenv("TERMINAIR_MOCK_SNOWFLAKE", raising=False)
    from terminair.dbt.snowflake_client import SnowflakeClient

    sc = SnowflakeClient(fixture_path=FIXTURE_PATH)
    assert sc.get_bytes_scanned("fct_revenue_daily") is None


# ---------------------------------------------------------------------------
# No module-level side effects
# ---------------------------------------------------------------------------

def test_no_module_level_file_read(monkeypatch):
    """Importing the module must not read query_history.json.

    We verify by checking there are no top-level reads during import — the
    module is already imported at this point so we just verify the class
    doesn't have a pre-loaded data attribute at class level (only instance level).
    """
    from terminair.dbt import snowflake_client as m

    # _mock_data must not be a class-level attribute
    assert not hasattr(m.SnowflakeClient, "_mock_data"), (
        "_mock_data should be an instance attribute, not a class attribute"
    )
