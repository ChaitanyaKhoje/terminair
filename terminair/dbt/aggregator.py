"""StateAggregator — single composition root merging all dbt data sources into list[ModelState]."""

from __future__ import annotations

from typing import TYPE_CHECKING

from terminair.dbt.models import ModelState
from terminair.logging_utils import get_logger

if TYPE_CHECKING:
    from terminair.dbt.airflow_bridge import AirflowBridge
    from terminair.dbt.artifacts import ArtifactReader
    from terminair.dbt.manifest import ManifestLoader
    from terminair.dbt.snowflake_client import SnowflakeClient

_log = get_logger(__name__)


class StateAggregator:
    """Single composition root that merges ManifestLoader, ArtifactReader,
    AirflowBridge, and SnowflakeClient into a list[ModelState].

    Screens should call get_models() and never access data sources directly.

    Usage::

        agg = StateAggregator(manifest, artifacts, bridge=bridge, snowflake=sc)
        models = await agg.get_models()
    """

    def __init__(
        self,
        manifest: ManifestLoader,
        artifacts: ArtifactReader,
        bridge: AirflowBridge | None = None,
        snowflake: SnowflakeClient | None = None,
    ) -> None:
        self._manifest = manifest
        self._artifacts = artifacts
        self._bridge = bridge
        self._snowflake = snowflake

    async def get_models(self) -> list[ModelState]:
        """Return one ModelState per manifest node, merging all data sources.

        Airflow and Snowflake failures are non-fatal: affected fields fall back
        to None rather than raising.
        """
        # ------------------------------------------------------------------ #
        # Optional: fetch Airflow task statuses
        # ------------------------------------------------------------------ #
        airflow_statuses: dict[str, tuple[str, str | None]] = {}
        if self._bridge is not None:
            try:
                all_node_ids = self._manifest.get_all_node_ids()
                node_names = [nid.split(".")[-1] for nid in all_node_ids]
                # dag_names unknown at this layer — bridge returns {} for []
                airflow_statuses = await self._bridge.get_task_statuses([], node_names)
            except Exception as e:  # pragma: no cover
                _log.warning(
                    "AirflowBridge failed: %s — proceeding without Airflow status",
                    str(e)[:80],
                )

        # ------------------------------------------------------------------ #
        # Build one ModelState per manifest node
        # ------------------------------------------------------------------ #
        models: list[ModelState] = []

        for node_id in self._manifest.get_all_node_ids():
            node = self._manifest.get_node(node_id)
            if node is None:  # should not happen — node_id came from get_all_node_ids
                continue

            # Basic node metadata
            name = node.get("name", node_id.split(".")[-1])
            all_tags: list[str] = node.get("tags", [])
            tag = all_tags[0] if all_tags else "untagged"
            config = self._manifest.get_config(node_id)
            materialization = config.get("materialized", "unknown")
            schema_name = node.get("schema", "")
            database_name = node.get("database", "")

            # Run result (current)
            result = self._artifacts.get_result(node_id)
            if result is not None:
                raw_status = result.get("status", "unknown")
                # Normalize Airflow/dbt "error" → "failed"
                status = "failed" if raw_status == "error" else raw_status
                duration_s = result.get("execution_time")
                error_message = result.get("message") if status == "failed" else None
            else:
                status = "unknown"
                duration_s = None
                error_message = None

            # Timing
            started_at, finished_at = self._artifacts.get_timing(node_id)

            # Row counts
            rows_written = self._artifacts.get_rows_affected(node_id)

            # Previous result for row delta
            prev_result = self._artifacts.get_previous_result(node_id)
            if prev_result is not None:
                rows_previous = prev_result.get("adapter_response", {}).get("rows_affected")
            else:
                rows_previous = None

            # row_delta_pct — None if either missing or division by zero
            if (
                rows_written is not None
                and rows_previous is not None
                and rows_previous != 0
            ):
                row_delta_pct: float | None = (
                    (rows_written - rows_previous) / rows_previous * 100
                )
            else:
                row_delta_pct = None

            # ---------------------------------------------------------------- #
            # Airflow enrichment (optional)
            # ---------------------------------------------------------------- #
            airflow_data = airflow_statuses.get(name)
            if airflow_data and airflow_data[0] is not None:
                task_id = name
                pod_name: str | None = airflow_data[1]
            else:
                task_id = ""
                pod_name = None

            # ---------------------------------------------------------------- #
            # Snowflake enrichment (optional)
            # ---------------------------------------------------------------- #
            bytes_scanned: int | None = (
                self._snowflake.get_bytes_scanned(name) if self._snowflake else None
            )

            # ---------------------------------------------------------------- #
            # Lineage
            # ---------------------------------------------------------------- #
            upstream_deps = self._manifest.get_upstream_deps(node_id)
            downstream_deps = self._manifest.get_downstream_deps(node_id)

            # Build upstream_statuses dict — for each upstream dep, lookup artifact status
            upstream_statuses: dict[str, str] = {}
            for dep_id in upstream_deps:
                dep_result = self._artifacts.get_result(dep_id)
                if dep_result is not None:
                    raw_dep_status = dep_result.get("status", "unknown")
                    # Normalize error → failed in upstream statuses too
                    dep_status = "failed" if raw_dep_status == "error" else raw_dep_status
                else:
                    dep_status = "unknown"
                upstream_statuses[dep_id] = dep_status

            # has_upstream_failure: True if any upstream is failed OR skipped
            has_upstream_failure = any(
                v in ("failed", "skipped") for v in upstream_statuses.values()
            )

            # ---------------------------------------------------------------- #
            # Manifest-derived fields
            # ---------------------------------------------------------------- #
            grain_columns = self._manifest.get_grain_columns(node_id)
            refs = self._manifest.get_refs(node_id)
            sources = self._manifest.get_sources(node_id)
            dbt_vars = self._manifest.get_dbt_vars(node_id)
            config_block = config

            # compiled_sql comes from manifest "compiled_code" JSON key
            compiled_sql: str | None = node.get("compiled_code")

            # dag_id: use first all_tag as a hint; default to empty string
            dag_id = ""

            models.append(
                ModelState(
                    node_id=node_id,
                    name=name,
                    tag=tag,
                    status=status,
                    dag_id=dag_id,
                    task_id=task_id,
                    materialization=materialization,
                    schema_name=schema_name,
                    database_name=database_name,
                    has_upstream_failure=has_upstream_failure,
                    all_tags=all_tags,
                    duration_s=duration_s,
                    rows_written=rows_written,
                    rows_previous=rows_previous,
                    row_delta_pct=row_delta_pct,
                    bytes_scanned=bytes_scanned,
                    pod_name=pod_name,
                    warehouse=None,
                    error_message=error_message,
                    upstream_deps=upstream_deps,
                    downstream_deps=downstream_deps,
                    upstream_statuses=upstream_statuses,
                    grain_columns=grain_columns,
                    refs=refs,
                    sources=sources,
                    dbt_vars=dbt_vars,
                    config_block=config_block,
                    compiled_sql=compiled_sql,
                    run_started_at=started_at,
                    run_finished_at=finished_at,
                )
            )

        return models
