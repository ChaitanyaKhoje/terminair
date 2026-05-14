"""Tests for RegressionAnalyzer and MockDataProvider — RED phase for TDD."""

from __future__ import annotations

import asyncio
import inspect

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


class TestMockDataProvider:
    def test_import(self):
        from terminair.dbt.mock_data import MockDataProvider  # noqa: F401

    def test_get_models_returns_10(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        assert len(models) == 10

    def test_get_models_is_async(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        assert inspect.iscoroutinefunction(mdp.get_models)

    def test_status_distribution(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        statuses = [m.status for m in models]
        assert statuses.count("running") == 2
        assert statuses.count("failed") == 2
        assert statuses.count("queued") == 2
        assert statuses.count("success") == 4

    def test_tag_distribution(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        tags = [m.tag for m in models]
        assert tags.count("finance") == 3
        assert tags.count("marketing") == 2
        assert tags.count("core") == 2
        assert tags.count("platform") == 2
        assert tags.count("risk") == 1

    def test_tick_transitions_running_to_success_after_4(self):
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        initial_models = asyncio.run(mdp.get_models())
        assert sum(1 for m in initial_models if m.status == "running") == 2

        for _ in range(4):
            mdp.tick()

        models_after = asyncio.run(mdp.get_models())
        running_after = [m for m in models_after if m.status == "running"]
        assert len(running_after) == 1, f"Expected 1 running after 4 ticks, got {len(running_after)}"

    def test_row_drop_signals_present(self):
        """At least 2 models have row_delta_pct < -25% for row_drop signals."""
        from terminair.dbt.mock_data import MockDataProvider
        from terminair.dbt.regression import RegressionAnalyzer

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        ra = RegressionAnalyzer(models)
        signals = ra.analyze()
        row_drops = [s for s in signals if s.signal_type == "row_drop"]
        assert len(row_drops) >= 2, f"Expected at least 2 row_drop signals, got {row_drops}"

    def test_new_model_no_baseline_signal_present(self):
        """fct_platform_events has rows_previous=None + status=success → INFO signal."""
        from terminair.dbt.mock_data import MockDataProvider
        from terminair.dbt.regression import RegressionAnalyzer

        mdp = MockDataProvider()
        models = asyncio.run(mdp.get_models())
        ra = RegressionAnalyzer(models)
        signals = ra.analyze()
        no_baseline = [s for s in signals if s.signal_type == "new_model_no_baseline"]
        assert len(no_baseline) >= 1

    def test_tick_increments_running_duration(self):
        """After 1 tick, running models have duration_s > initial value."""
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        initial_models = asyncio.run(mdp.get_models())
        initial_durations = {m.name: m.duration_s for m in initial_models if m.status == "running"}

        mdp.tick()

        models_after = asyncio.run(mdp.get_models())
        after_durations = {m.name: m.duration_s for m in models_after if m.status == "running"}

        for name, initial_dur in initial_durations.items():
            if name in after_durations:
                assert after_durations[name] > (initial_dur or 0.0), (
                    f"{name} duration should have increased after tick"
                )

    def test_tick_recomputes_row_delta_pct(self):
        """After 4 ticks, the transitioned model has status=success and row_delta_pct is not None."""
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        initial_models = asyncio.run(mdp.get_models())
        # Record initial running model names
        initial_running = [m.name for m in initial_models if m.status == "running"]
        assert len(initial_running) == 2

        for _ in range(4):
            mdp.tick()

        models_after = asyncio.run(mdp.get_models())
        # One model should have transitioned from running → success
        transitioned = [
            m for m in models_after
            if m.name in initial_running and m.status == "success"
        ]
        assert len(transitioned) == 1, f"Expected 1 transitioned model, got {transitioned}"
        # The transitioned model should have row_delta_pct computed (not None)
        assert transitioned[0].row_delta_pct is not None

    def test_get_models_returns_copy(self):
        """Mutating the returned list does not affect internal state."""
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        models1 = asyncio.run(mdp.get_models())
        models1.clear()  # Mutate the returned list
        models2 = asyncio.run(mdp.get_models())
        assert len(models2) == 10, "Internal state was mutated — get_models() must return a copy"
