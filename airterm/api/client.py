"""Read-only async HTTP client for the Airflow REST API."""

from typing import Dict, Optional

import httpx
import logging

from airterm.api import models
from airterm.api.auth import build_auth
from airterm.config import Connection


# Lightweight module logger that writes to the TUI debug log so failures in
# parsing remote API responses are visible to users running locally.
_LOG_PATH = "/tmp/airterm-debug.log"
_logger = logging.getLogger("airterm.api.client")
if not _logger.handlers:
    try:
        fh = logging.FileHandler(_LOG_PATH, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _logger.addHandler(fh)
        _logger.setLevel(logging.DEBUG)
    except Exception:
        pass


class AirflowClient:
    """Read only async client for the Airflow REST API.
    Only GET methods. No mutations."""

    def __init__(self, config: Connection):
        self._base_url = config.url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=build_auth(config.auth),
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10),
        )

    async def close(self):
        await self._client.aclose()

    async def get_dags(
        self,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[str] = None,
        owners: Optional[str] = None,
    ) -> models.DagList:
        params = {"limit": limit, "offset": offset}
        if tags:
            params["tags"] = tags
        if owners:
            params["owners"] = owners
        resp = await self._client.get("/api/v1/dags", params=params)
        resp.raise_for_status()
        return models.DagList(**resp.json())

    async def get_dag(self, dag_id: str) -> models.Dag:
        resp = await self._client.get(f"/api/v1/dags/{dag_id}")
        resp.raise_for_status()
        return models.Dag(**resp.json())

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "-execution_date",
    ) -> models.DagRunList:
        resp = await self._client.get(
            f"/api/v1/dags/{dag_id}/dagRuns",
            params={"limit": limit, "offset": offset, "order_by": order_by},
        )
        resp.raise_for_status()
        return models.DagRunList(**resp.json())

    async def get_all_dag_runs(
        self,
        limit: int = 50,
        order_by: str = "-end_date",
        end_date_gte: Optional[str] = None,
    ) -> models.DagRunList:
        params = {"limit": limit, "order_by": order_by}
        if end_date_gte:
            params["end_date_gte"] = end_date_gte
        resp = await self._client.get("/api/v1/dags/-/dagRuns", params=params)
        resp.raise_for_status()
        return models.DagRunList(**resp.json())

    async def get_task_instances(
        self,
        dag_id: str,
        run_id: str,
    ) -> models.TaskInstanceList:
        resp = await self._client.get(
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances",
        )
        resp.raise_for_status()
        return models.TaskInstanceList(**resp.json())

    async def get_all_task_instances(
        self,
        start_date_gte: Optional[str] = None,
        end_date_gte: Optional[str] = None,
        end_date_lte: Optional[str] = None,
        limit: int = 500,
    ) -> models.TaskInstanceList:
        """Fetch task instances across all DAGs (bulk endpoint)."""
        params: Dict[str, str] = {"limit": str(limit)}
        if start_date_gte:
            params["start_date_gte"] = start_date_gte
        if end_date_gte:
            params["end_date_gte"] = end_date_gte
        if end_date_lte:
            params["end_date_lte"] = end_date_lte
        resp = await self._client.get(
            "/api/v1/dags/-/dagRuns/-/taskInstances",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return models.TaskInstanceList(**data)
        except Exception as e:
            # Be forgiving: log the parsing error and attempt to build a
            # minimal `TaskInstanceList` from the returned JSON if possible.
            try:
                _logger.debug(f"get_all_task_instances: parse failed: {e}")
                keys = list(data.keys()) if isinstance(data, dict) else []
                _logger.debug(f"get_all_task_instances: response keys={keys}")
            except Exception:
                pass
            tis = []
            raw_list = data.get("task_instances", []) if isinstance(data, dict) else []
            for ti in raw_list:
                try:
                    tis.append(models.TaskInstance(**ti))
                except Exception:
                    # skip invalid items
                    continue
            return models.TaskInstanceList(task_instances=tis)

    async def get_task_log(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int = 1,
    ) -> str:
        resp = await self._client.get(
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
        )
        resp.raise_for_status()
        return resp.text

    async def get_dag_details(self, dag_id: str) -> models.DAGDetails:
        resp = await self._client.get(f"/api/v1/dags/{dag_id}/details")
        resp.raise_for_status()
        return models.DAGDetails(**resp.json())

    async def get_dag_tasks(self, dag_id: str) -> models.DAGTaskList:
        resp = await self._client.get(f"/api/v1/dags/{dag_id}/tasks")
        resp.raise_for_status()
        data = resp.json()
        tasks = [models.DAGTask(**t) for t in data.get("tasks", [])]
        return models.DAGTaskList(tasks=tasks, total_entries=data.get("total_entries", len(tasks)))

    async def get_pools(self) -> models.PoolList:
        resp = await self._client.get("/api/v1/pools")
        resp.raise_for_status()
        data = resp.json()
        try:
            return models.PoolList(**data)
        except Exception as e:
            try:
                _logger.debug(f"get_pools: parse failed: {e}")
                keys = list(data.keys()) if isinstance(data, dict) else []
                _logger.debug(f"get_pools: response keys={keys}")
            except Exception:
                pass
            pools_raw = data.get("pools", []) if isinstance(data, dict) else []
            pools = []
            for p in pools_raw:
                try:
                    pools.append(models.Pool(**p))
                except Exception:
                    continue
            return models.PoolList(pools=pools)

    async def get_health(self) -> models.HealthInfo:
        resp = await self._client.get("/api/v1/health")
        resp.raise_for_status()
        return models.HealthInfo(**resp.json())

    async def get_import_errors(self) -> models.ImportErrorList:
        resp = await self._client.get("/api/v1/importErrors")
        resp.raise_for_status()
        return models.ImportErrorList(**resp.json())

    async def get_event_logs(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> models.EventLogList:
        resp = await self._client.get(
            "/api/v1/eventLogs",
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        return models.EventLogList(**resp.json())

    async def get_xcom_entries(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        limit: int = 20,
    ) -> models.XComEntryList:
        resp = await self._client.get(
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries",
            params={"limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        entries = []
        for e in data.get("xcom_entries", []):
            entries.append(models.XComEntry(**e))
        return models.XComEntryList(
            xcom_entries=entries,
            total_entries=data.get("total_entries", len(entries)),
        )

    async def get_xcom_value(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        xcom_key: str,
    ) -> str:
        resp = await self._client.get(
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries/{xcom_key}",
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("value", ""))

    async def get_sla_misses(self, dag_id: str) -> models.SlaMissList:
        resp = await self._client.get(
            "/api/v1/dagWarnings",
            params={"dag_id": dag_id, "warning_type": "task_not_finished"},
        )
        # SLA endpoint may not exist on all versions — return empty on 404
        if resp.status_code == 404:
            return models.SlaMissList()
        resp.raise_for_status()
        data = resp.json()
        items = [models.SlaMissItem(**i) for i in data.get("dag_warnings", [])]
        return models.SlaMissList(sla_miss=items, total_entries=len(items))

    async def get_datasets(self) -> models.DatasetList:
        resp = await self._client.get("/api/v1/datasets")
        resp.raise_for_status()
        return models.DatasetList(**resp.json())

    async def get_dataset_events(self) -> models.DatasetEventList:
        resp = await self._client.get("/api/v1/datasets/events")
        resp.raise_for_status()
        return models.DatasetEventList(**resp.json())
