"""dbt run_results.json reader — per-node status, timing, row counts, error messages."""

from __future__ import annotations

import json
from pathlib import Path

from terminair.logging_utils import get_logger

_log = get_logger(__name__)


class ArtifactReader:
    """Load and query dbt run_results.json artifacts."""

    def __init__(
        self,
        results_path: Path,
        previous_path: Path | None = None,
    ) -> None:
        results_path = Path(results_path)
        if not results_path.exists():
            raise FileNotFoundError(f"run_results.json not found: {results_path}")

        with open(results_path) as f:
            data = json.load(f)

        self._index: dict[str, dict] = {
            r["unique_id"]: r for r in data.get("results", [])
        }
        _log.debug("ArtifactReader loaded %d results from %s", len(self._index), results_path)

        self._prev_index: dict[str, dict] | None = None
        if previous_path is not None:
            previous_path = Path(previous_path)
            if previous_path.exists():
                with open(previous_path) as f:
                    prev_data = json.load(f)
                self._prev_index = {
                    r["unique_id"]: r for r in prev_data.get("results", [])
                }
                _log.debug("ArtifactReader loaded %d previous results", len(self._prev_index))

    def get_result(self, node_id: str) -> dict | None:
        return self._index.get(node_id)

    def get_previous_result(self, node_id: str) -> dict | None:
        if self._prev_index is None:
            return None
        return self._prev_index.get(node_id)

    def get_all_node_ids(self) -> list[str]:
        return list(self._index.keys())

    def get_rows_affected(self, node_id: str) -> int | None:
        result = self.get_result(node_id)
        if result is None:
            return None
        return result.get("adapter_response", {}).get("rows_affected")

    def get_execution_time(self, node_id: str) -> float | None:
        result = self.get_result(node_id)
        if result is None:
            return None
        return result.get("execution_time")

    def get_timing(self, node_id: str) -> tuple[str | None, str | None]:
        result = self.get_result(node_id)
        if result is None:
            return (None, None)
        timing = result.get("timing", [])
        execute_step = next((t for t in timing if t.get("name") == "execute"), None)
        if execute_step is None:
            return (None, None)
        return (execute_step.get("started_at"), execute_step.get("completed_at"))
