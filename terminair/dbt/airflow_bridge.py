"""AirflowBridge — async GET-only Airflow REST client with fuzzy task→node matching."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

import httpx

from terminair.api.auth import build_auth
from terminair.logging_utils import get_logger, sanitize_error

if TYPE_CHECKING:
    from terminair.config import Connection

_log = get_logger(__name__)

# Airflow task state → terminair canonical status mapping
_STATE_MAP: dict[str, str] = {
    "running": "running",
    "success": "success",
    "failed": "failed",
    "queued": "queued",
    "skipped": "skipped",
    "upstream_failed": "failed",
    "none": "queued",
}


class AirflowBridgeError(Exception):
    """Raised when the Airflow REST API call fails."""


def _fuzzy_match(task_id: str, node_names: list[str]) -> str | None:
    """Match a task_id string to the closest manifest node name.

    Strategy:
      1. Substring check (case-insensitive) — handles prefix patterns like
         'run_fct_revenue_daily' → 'fct_revenue_daily'.
      2. difflib.get_close_matches fallback with cutoff=0.6.

    Returns the matched node name, or None if no match found.
    """
    task_lower = task_id.lower()
    for name in node_names:
        name_lower = name.lower()
        if name_lower in task_lower or task_lower in name_lower:
            return name

    matches = difflib.get_close_matches(task_id, node_names, n=1, cutoff=0.6)
    return matches[0] if matches else None


class AirflowBridge:
    """Async GET-only client for the Airflow REST API.

    Provides fuzzy task→node matching so Airflow task_id strings (which often
    have prefixes like 'run_' or suffixes like '_v2') can be correlated with
    manifest node short names.

    Usage::

        bridge = AirflowBridge(connection)
        try:
            statuses = await bridge.get_task_statuses(dag_names, node_names)
        finally:
            await bridge.close()
    """

    def __init__(self, connection: Connection) -> None:
        """Construct the bridge.  No HTTP calls are made in __init__."""
        self._client = httpx.AsyncClient(
            base_url=str(connection.url),
            auth=build_auth(connection.auth),
            timeout=10.0,
        )

    async def get_task_statuses(
        self,
        dag_names: list[str],
        node_names: list[str],
    ) -> dict[str, tuple[str, str | None]]:
        """Return {matched_node_name: (status, hostname_or_None)} for latest runs.

        For each dag_id in *dag_names*, fetches the most recent DAG run and its
        task instances.  Each task_id is fuzzy-matched against *node_names*; only
        matched tasks are included in the result.

        Airflow REST endpoints used (GET only):
          - GET /api/v1/dags/{dag_id}/dagRuns?limit=1&order_by=-execution_date
          - GET /api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances

        Returns an empty dict when Airflow is unreachable or no runs exist.
        """
        result: dict[str, tuple[str, str | None]] = {}

        for dag_id in dag_names:
            try:
                # Fetch the most recent dag run
                resp = await self._client.get(
                    f"/api/v1/dags/{dag_id}/dagRuns",
                    params={"limit": 1, "order_by": "-execution_date"},
                )
                resp.raise_for_status()
                runs = resp.json().get("dag_runs", [])
                if not runs:
                    continue

                dag_run_id = runs[0]["dag_run_id"]

                # Fetch task instances for this run
                resp = await self._client.get(
                    f"/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
                )
                resp.raise_for_status()

                for ti in resp.json().get("task_instances", []):
                    task_id = ti["task_id"]
                    matched_name = _fuzzy_match(task_id, node_names)
                    if matched_name is None:
                        continue

                    raw_state = ti.get("state", "unknown")
                    status = _STATE_MAP.get(raw_state, "unknown")
                    hostname = ti.get("hostname")  # may be None or empty string
                    result[matched_name] = (status, hostname or None)

            except httpx.HTTPError as exc:
                safe_msg = sanitize_error(str(exc))
                _log.warning("AirflowBridge: request failed for dag '%s': %s", dag_id, safe_msg)
                raise AirflowBridgeError(safe_msg) from exc

        return result

    async def close(self) -> None:
        """Close the underlying httpx AsyncClient to prevent ResourceWarning."""
        await self._client.aclose()
