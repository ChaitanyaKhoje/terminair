"""Tests for RegressionAnalyzer — all 6 signal types and severity thresholds."""

from __future__ import annotations

import pytest

from terminair.dbt.models import Severity


class TestRegressionAnalyzer:
    def test_import(self):
        from terminair.dbt.regression import RegressionAnalyzer  # noqa: F401

    def test_row_drop_warning_threshold(self):
        """delta < -10% but > -30% → WARNING row_drop."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            rows_written=15000,
            rows_previous=20000,
            row_delta_pct=-25.0,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        row_drops = [s for s in signals if s.signal_type == "row_drop"]
        assert len(row_drops) == 1
        assert row_drops[0].severity == Severity.WARNING

    def test_row_drop_critical_threshold(self):
        """delta < -30% → CRITICAL row_drop."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.mart_platform_usage",
            name="mart_platform_usage",
            tag="platform",
            status="success",
            dag_id="",
            task_id="",
            materialization="table",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            rows_written=890000,
            rows_previous=1500000,
            row_delta_pct=-40.67,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        row_drops = [s for s in signals if s.signal_type == "row_drop"]
        assert len(row_drops) == 1
        assert row_drops[0].severity == Severity.CRITICAL

    def test_new_model_no_baseline_info(self):
        """rows_previous=None AND status=success → INFO new_model_no_baseline."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.fct_platform_events",
            name="fct_platform_events",
            tag="platform",
            status="success",
            dag_id="",
            task_id="",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            rows_written=44000,
            rows_previous=None,
            row_delta_pct=None,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        no_baseline = [s for s in signals if s.signal_type == "new_model_no_baseline"]
        assert len(no_baseline) == 1
        assert no_baseline[0].severity == Severity.INFO

    def test_signals_sorted_critical_first(self):
        """When multiple signals exist, CRITICAL before WARNING before INFO."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        models = [
            ModelState(
                node_id="model.p.a",
                name="a",
                tag="t",
                status="success",
                dag_id="",
                task_id="",
                materialization="table",
                schema_name="s",
                database_name="d",
                has_upstream_failure=False,
                row_delta_pct=-25.0,  # WARNING row_drop
            ),
            ModelState(
                node_id="model.p.b",
                name="b",
                tag="t",
                status="success",
                dag_id="",
                task_id="",
                materialization="table",
                schema_name="s",
                database_name="d",
                has_upstream_failure=False,
                row_delta_pct=-40.0,  # CRITICAL row_drop
            ),
            ModelState(
                node_id="model.p.c",
                name="c",
                tag="t",
                status="success",
                dag_id="",
                task_id="",
                materialization="table",
                schema_name="s",
                database_name="d",
                has_upstream_failure=False,
                rows_previous=None,  # INFO new_model_no_baseline
            ),
        ]
        ra = RegressionAnalyzer(models)
        signals = ra.analyze()
        assert len(signals) >= 3
        assert signals[0].severity == Severity.CRITICAL
        assert signals[-1].severity == Severity.INFO

    def test_grain_added_warning(self):
        """Current grain_columns > previous → WARNING grain_added."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        prev = ModelState(
            node_id="model.p.fct_risk_exposure",
            name="fct_risk_exposure",
            tag="risk",
            status="success",
            dag_id="",
            task_id="",
            materialization="incremental",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            grain_columns=["risk_date"],
        )
        curr = ModelState(
            node_id="model.p.fct_risk_exposure",
            name="fct_risk_exposure",
            tag="risk",
            status="success",
            dag_id="",
            task_id="",
            materialization="incremental",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            grain_columns=["risk_date", "entity_id"],
        )
        ra = RegressionAnalyzer([curr])
        signals = ra.analyze([prev])
        grain_added = [s for s in signals if s.signal_type == "grain_added"]
        assert len(grain_added) == 1
        assert grain_added[0].severity == Severity.WARNING

    def test_grain_removed_critical(self):
        """Current grain_columns < previous → CRITICAL grain_removed."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        prev = ModelState(
            node_id="model.p.fct_risk_exposure",
            name="fct_risk_exposure",
            tag="risk",
            status="success",
            dag_id="",
            task_id="",
            materialization="incremental",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            grain_columns=["risk_date", "entity_id"],
        )
        curr = ModelState(
            node_id="model.p.fct_risk_exposure",
            name="fct_risk_exposure",
            tag="risk",
            status="success",
            dag_id="",
            task_id="",
            materialization="incremental",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            grain_columns=["risk_date"],  # removed entity_id
        )
        ra = RegressionAnalyzer([curr])
        signals = ra.analyze([prev])
        grain_removed = [s for s in signals if s.signal_type == "grain_removed"]
        assert len(grain_removed) == 1
        assert grain_removed[0].severity == Severity.CRITICAL

    def test_signals_for_model(self):
        """signals_for_model() filters by node_id."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            row_delta_pct=-25.0,
        )
        ra = RegressionAnalyzer([model])
        ra.analyze()
        signals = ra.signals_for_model("model.p.stg_orders")
        assert len(signals) >= 1
        assert all(s.node_id == "model.p.stg_orders" for s in signals)

    def test_row_spike_warning(self):
        """row_delta_pct > 50% → WARNING row_spike signal."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            row_delta_pct=75.0,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        row_spikes = [s for s in signals if s.signal_type == "row_spike"]
        assert len(row_spikes) == 1
        assert row_spikes[0].severity == Severity.WARNING

    def test_row_spike_below_threshold_no_signal(self):
        """row_delta_pct <= 50% → no row_spike signal."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            row_delta_pct=30.0,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        row_spikes = [s for s in signals if s.signal_type == "row_spike"]
        assert len(row_spikes) == 0

    def test_new_model_no_baseline_not_triggered_if_not_success(self):
        """rows_previous=None AND status != 'success' → no new_model_no_baseline signal."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        model = ModelState(
            node_id="model.p.some_model",
            name="some_model",
            tag="core",
            status="failed",
            dag_id="",
            task_id="",
            materialization="table",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            rows_previous=None,
            rows_written=None,
        )
        ra = RegressionAnalyzer([model])
        signals = ra.analyze()
        no_baseline = [s for s in signals if s.signal_type == "new_model_no_baseline"]
        assert len(no_baseline) == 0

    def test_upstream_schema_change_warning(self):
        """upstream dep changes materialization → WARNING upstream_schema_change on consumer."""
        from terminair.dbt.regression import RegressionAnalyzer
        from terminair.dbt.models import ModelState

        prev_upstream = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="view",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
        )
        curr_upstream = ModelState(
            node_id="model.p.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="table",  # changed from view → table
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
        )
        consumer = ModelState(
            node_id="model.p.fct_orders",
            name="fct_orders",
            tag="core",
            status="success",
            dag_id="",
            task_id="",
            materialization="table",
            schema_name="s",
            database_name="d",
            has_upstream_failure=False,
            upstream_deps=["model.p.stg_orders"],
        )
        ra = RegressionAnalyzer([consumer, curr_upstream])
        signals = ra.analyze(previous=[prev_upstream])
        upstream_changes = [s for s in signals if s.signal_type == "upstream_schema_change"]
        assert len(upstream_changes) == 1
        assert upstream_changes[0].severity == Severity.WARNING
        assert upstream_changes[0].node_id == "model.p.fct_orders"

        # Guard: upstream node must not emit upstream_schema_change against itself
        upstream_self_signals = [
            s for s in signals
            if s.node_id == "model.p.stg_orders" and s.signal_type == "upstream_schema_change"
        ]
        assert len(upstream_self_signals) == 0, (
            "upstream node should not emit upstream_schema_change against itself"
        )

        # Total signal count: 1 upstream_schema_change (fct_orders) +
        # 1 new_model_no_baseline (stg_orders, rows_previous=None + status=success)
        assert len(signals) == 2, (
            f"Expected exactly 2 signals total, got {len(signals)}: "
            f"{[(s.signal_type, s.node_id) for s in signals]}"
        )
