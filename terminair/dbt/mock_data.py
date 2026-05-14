"""MockDataProvider — drop-in for StateAggregator; 10 demo models, no external services."""

from __future__ import annotations

from terminair.dbt.models import ModelState


def _build_initial_models() -> list[ModelState]:
    """Construct the 10 demo ModelState instances for MockDataProvider.

    Tag distribution: finance(3), marketing(2), core(2), platform(2), risk(1)
    Status distribution: 2 running, 2 failed, 2 queued, 4 success

    Two models have row_delta_pct < -25% (row_drop signals).
    One model has rows_previous=None + status=success (new_model_no_baseline signal).
    """
    return [
        # ------------------------------------------------------------------ #
        # finance (3 models)
        # ------------------------------------------------------------------ #
        ModelState(
            node_id="model.my_project.fct_revenue_daily",
            name="fct_revenue_daily",
            tag="finance",
            status="running",
            dag_id="dbt_finance_daily",
            task_id="fct_revenue_daily",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["finance"],
            duration_s=42.0,
            rows_written=None,
            rows_previous=22000,
            row_delta_pct=None,
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
            grain_columns=["revenue_date"],
        ),
        ModelState(
            node_id="model.my_project.fct_orders",
            name="fct_orders",
            tag="finance",
            status="running",
            dag_id="dbt_finance_daily",
            task_id="fct_orders",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["finance"],
            duration_s=75.0,
            rows_written=None,
            rows_previous=18000,
            row_delta_pct=None,
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
            upstream_deps=[
                "model.my_project.stg_orders",
                "model.my_project.stg_payments",
            ],
            upstream_statuses={
                "model.my_project.stg_orders": "success",
                "model.my_project.stg_payments": "success",
            },
            grain_columns=["order_id"],
        ),
        ModelState(
            node_id="model.my_project.mart_finance_summary",
            name="mart_finance_summary",
            tag="finance",
            status="failed",
            dag_id="dbt_finance_daily",
            task_id="mart_finance_summary",
            materialization="table",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["finance"],
            duration_s=None,
            rows_written=None,
            rows_previous=55000,
            row_delta_pct=None,
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
            error_message=(
                "Snowflake SQL compilation error: Object 'ANALYTICS.STG_PAYMENTS'"
                " does not exist"
            ),
        ),
        # ------------------------------------------------------------------ #
        # marketing (2 models)
        # ------------------------------------------------------------------ #
        ModelState(
            node_id="model.my_project.stg_campaign_events",
            name="stg_campaign_events",
            tag="marketing",
            status="queued",
            dag_id="dbt_marketing_daily",
            task_id="stg_campaign_events",
            materialization="view",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["marketing"],
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
        ),
        ModelState(
            node_id="model.my_project.fct_campaign_attribution",
            name="fct_campaign_attribution",
            tag="marketing",
            status="failed",
            dag_id="dbt_marketing_daily",
            task_id="fct_campaign_attribution",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=True,
            all_tags=["marketing"],
            duration_s=None,
            rows_written=None,
            rows_previous=31000,
            row_delta_pct=None,
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
            error_message=None,
            upstream_deps=["model.my_project.stg_campaign_events"],
            upstream_statuses={"model.my_project.stg_campaign_events": "queued"},
        ),
        # ------------------------------------------------------------------ #
        # core (2 models)
        # ------------------------------------------------------------------ #
        ModelState(
            node_id="model.my_project.stg_orders",
            name="stg_orders",
            tag="core",
            status="success",
            dag_id="dbt_finance_daily",
            task_id="stg_orders",
            materialization="view",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["core"],
            rows_written=15000,
            rows_previous=20000,
            row_delta_pct=-25.0,  # row_drop WARNING
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
        ),
        ModelState(
            node_id="model.my_project.stg_payments",
            name="stg_payments",
            tag="core",
            status="success",
            dag_id="dbt_finance_daily",
            task_id="stg_payments",
            materialization="view",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["core"],
            rows_written=12500,
            rows_previous=12800,
            row_delta_pct=-2.34,  # no signal — below -10%
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
        ),
        # ------------------------------------------------------------------ #
        # platform (2 models)
        # ------------------------------------------------------------------ #
        ModelState(
            node_id="model.my_project.mart_platform_usage",
            name="mart_platform_usage",
            tag="platform",
            status="success",
            dag_id="dbt_platform_daily",
            task_id="mart_platform_usage",
            materialization="table",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["platform"],
            rows_written=890000,
            rows_previous=1500000,
            row_delta_pct=-40.67,  # row_drop CRITICAL
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
        ),
        ModelState(
            node_id="model.my_project.fct_platform_events",
            name="fct_platform_events",
            tag="platform",
            status="success",
            dag_id="dbt_platform_daily",
            task_id="fct_platform_events",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["platform"],
            rows_written=44000,
            rows_previous=None,   # new_model_no_baseline INFO signal
            row_delta_pct=None,
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
        ),
        # ------------------------------------------------------------------ #
        # risk (1 model)
        # ------------------------------------------------------------------ #
        ModelState(
            node_id="model.my_project.fct_risk_exposure",
            name="fct_risk_exposure",
            tag="risk",
            status="queued",
            dag_id="dbt_risk_daily",
            task_id="fct_risk_exposure",
            materialization="incremental",
            schema_name="analytics",
            database_name="prod",
            has_upstream_failure=False,
            all_tags=["risk"],
            bytes_scanned=None,
            pod_name=None,
            warehouse=None,
            grain_columns=["risk_date", "entity_id"],
        ),
    ]


class MockDataProvider:
    """Drop-in for StateAggregator: 10 fixed demo ModelState instances, no services.

    The interface matches StateAggregator exactly:
        async def get_models(self) -> list[ModelState]

    tick() simulates time passing: running model durations increment by 5 s per call.
    After 4 calls the first running model transitions to success.

    Usage::

        mdp = MockDataProvider()
        models = await mdp.get_models()   # same signature as StateAggregator
        mdp.tick()                         # advance simulation time
    """

    def __init__(self) -> None:
        self._tick_count: int = 0
        self._models: list[ModelState] = _build_initial_models()

    async def get_models(self) -> list[ModelState]:
        """Return a copy of the current demo model list.

        Declared async def (no awaits) to match the StateAggregator interface exactly.
        inspect.iscoroutinefunction(mdp.get_models) returns True.
        """
        return list(self._models)

    def tick(self) -> None:
        """Advance the simulation by one tick (approximately 5 seconds).

        - Increments duration_s for all running models by 5.0 s.
        - After every 4th tick, transitions the first running model to success
          and recomputes its row_delta_pct.
        """
        self._tick_count += 1

        # Increment duration for running models
        for m in self._models:
            if m.status == "running":
                m.duration_s = (m.duration_s or 0.0) + 5.0

        # Every 4 ticks: transition first running model to success
        if self._tick_count % 4 == 0:
            for m in self._models:
                if m.status == "running":
                    m.status = "success"
                    m.rows_written = 22000  # simulate final row count
                    m.rows_previous = 22000
                    m.row_delta_pct = 0.0
                    break
