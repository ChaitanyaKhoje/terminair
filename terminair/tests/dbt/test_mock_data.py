"""Tests for MockDataProvider — tick() transitions, row_delta_pct recomputation, signal coverage."""

from __future__ import annotations

import asyncio
import inspect


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
        # Index all models by name (regardless of status) so transitioning
        # models are still checked — the old `if name in after_durations` guard
        # silently skipped them when they moved out of "running".
        after_by_name = {m.name: m for m in models_after}

        for name, initial_dur in initial_durations.items():
            m_after = after_by_name[name]  # model must still exist in results
            assert m_after.duration_s is not None, (
                f"{name} duration_s is None after tick"
            )
            assert m_after.duration_s > (initial_dur or 0.0), (
                f"{name} duration did not increase after tick"
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

    def test_get_previous_models_grain_shifted(self):
        """get_previous_models returns 10 models with deliberately shifted grain_columns."""
        from terminair.dbt.mock_data import MockDataProvider

        mdp = MockDataProvider()
        prev = asyncio.run(mdp.get_previous_models())
        assert len(prev) == 10
        fct_revenue = next(m for m in prev if m.name == "fct_revenue_daily")
        # grain_columns must differ from current (["revenue_date"])
        assert fct_revenue.grain_columns != ["revenue_date"]
        assert inspect.iscoroutinefunction(mdp.get_previous_models) is True

    def test_get_previous_models_enables_grain_signals(self):
        """RegressionAnalyzer with previous snapshot from MockDataProvider yields grain signals."""
        from terminair.dbt.mock_data import MockDataProvider
        from terminair.dbt.regression import RegressionAnalyzer

        mdp = MockDataProvider()
        current = asyncio.run(mdp.get_models())
        prev = asyncio.run(mdp.get_previous_models())
        signals = RegressionAnalyzer(current).analyze(previous=prev)
        grain_signal_types = {"grain_added", "grain_removed"}
        found = [s for s in signals if s.signal_type in grain_signal_types]
        assert len(found) >= 1, f"Expected at least one grain signal, got: {signals}"
