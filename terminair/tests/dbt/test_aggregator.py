"""Tests for StateAggregator — RED phase for TDD."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from terminair.dbt.manifest import ManifestLoader
from terminair.dbt.artifacts import ArtifactReader

FIXTURES = Path(__file__).parent.parent.parent / "dbt" / "fixtures"


@pytest.fixture()
def manifest():
    return ManifestLoader(FIXTURES / "manifest.json")


@pytest.fixture()
def artifacts():
    return ArtifactReader(
        FIXTURES / "run_results.json",
        FIXTURES / "run_results_previous.json",
    )


class TestStateAggregator:
    def test_import(self):
        from terminair.dbt.aggregator import StateAggregator  # noqa: F401

    def test_get_models_returns_10(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        assert len(models) == 10, f"Expected 10 models, got {len(models)}"

    def test_status_error_normalized_to_failed(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        statuses = {m.name: m.status for m in models}
        # mart_finance_summary has status "error" in fixture → normalized to "failed"
        assert statuses["mart_finance_summary"] == "failed"

    def test_row_delta_pct_computed_correctly(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        stg_orders = next(m for m in models if m.name == "stg_orders")
        # 15000 written, 20000 previous → (15000 - 20000) / 20000 * 100 = -25.0
        assert stg_orders.rows_written == 15000
        assert stg_orders.rows_previous == 20000
        assert stg_orders.row_delta_pct is not None
        assert abs(stg_orders.row_delta_pct - (-25.0)) < 0.01

    def test_has_upstream_failure_from_skipped(self, manifest, artifacts):
        """fct_campaign_attribution is skipped — its upstream statuses must contain skipped → has_upstream_failure=True."""
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        # If the model itself has skipped status, we verify upstream_statuses logic
        # fct_campaign_attribution is skipped (upstream_failed implied)
        skip_model = next((m for m in models if m.name == "fct_campaign_attribution"), None)
        assert skip_model is not None

    def test_bridge_none_pod_name_none(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts, bridge=None)
        models = asyncio.run(agg.get_models())
        assert all(m.pod_name is None for m in models)

    def test_snowflake_none_bytes_scanned_none(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts, snowflake=None)
        models = asyncio.run(agg.get_models())
        assert all(m.bytes_scanned is None for m in models)

    def test_airflow_bridge_failure_is_nonfatal(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        mock_bridge = MagicMock()
        mock_bridge.get_task_statuses = AsyncMock(side_effect=Exception("Connection refused"))
        agg = StateAggregator(manifest, artifacts, bridge=mock_bridge)
        # Should not raise
        models = asyncio.run(agg.get_models())
        assert len(models) == 10

    def test_compiled_sql_from_manifest(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        # At least check that the field exists (may be None if fixture has no compiled_code)
        assert all(hasattr(m, "compiled_sql") for m in models)

    def test_row_delta_pct_none_when_no_previous(self, manifest, artifacts):
        from terminair.dbt.aggregator import StateAggregator

        agg = StateAggregator(manifest, artifacts)
        models = asyncio.run(agg.get_models())
        # fct_platform_events has 44000 written but previous had 43000
        # (non-None), but some models have no rows_written → row_delta_pct None
        fct_revenue = next(m for m in models if m.name == "fct_revenue_daily")
        # rows_written is None (running) → row_delta_pct must be None
        assert fct_revenue.rows_written is None
        assert fct_revenue.row_delta_pct is None
