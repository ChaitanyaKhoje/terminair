"""Background poller for Airflow API data."""

import asyncio
from typing import Optional

from airterm.api.client import AirflowClient
from airterm.state import get_state


class Poller:
    """Background poller for Airflow API data."""

    def __init__(self, client: AirflowClient):
        self._client = client
        self._state = get_state()
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def start_polling(
        self,
        resource: str,
        interval: float,
        **params,
    ):
        """Start polling a resource. Replaces existing poll for same resource."""
        await self.stop_polling(resource)
        self._running = True
        task = asyncio.create_task(self._poll_loop(resource, interval, **params))
        self._tasks[resource] = task

    async def stop_polling(self, resource: str):
        """Stop polling a specific resource."""
        if resource in self._tasks:
            self._tasks[resource].cancel()
            try:
                await self._tasks[resource]
            except asyncio.CancelledError:
                pass
            del self._tasks[resource]

    async def stop_all(self):
        """Stop all active polls."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    async def _poll_loop(
        self,
        resource: str,
        interval: float,
        **params,
    ):
        in_flight = False
        while self._running:
            if not in_flight:
                in_flight = True
                try:
                    await self._poll_once(resource, **params)
                except Exception as e:
                    self._state.error_message = str(e)
                in_flight = False
            await asyncio.sleep(interval)

    async def _poll_once(self, resource: str, **params):
        if resource == "dags":
            result = await self._client.get_dags(**params)
            self._state.dags = result.dags
        elif resource == "dag_runs":
            dag_id = params.get("dag_id")
            if dag_id:
                result = await self._client.get_dag_runs(dag_id, **params)
                runs = dict(self._state.dag_runs)
                runs[dag_id] = result.dag_runs
                self._state.dag_runs = runs
        elif resource == "task_instances":
            dag_id = params.get("dag_id")
            run_id = params.get("run_id")
            if dag_id and run_id:
                result = await self._client.get_task_instances(dag_id, run_id)
                tis = dict(self._state.task_instances)
                key = f"{dag_id}:{run_id}"
                tis[key] = result.task_instances
                self._state.task_instances = tis
        elif resource == "pools":
            result = await self._client.get_pools()
            self._state.pools = result.pools
        elif resource == "health":
            result = await self._client.get_health()
            self._state.health = result


_default_poller: Optional[Poller] = None


def get_poller() -> Optional[Poller]:
    return _default_poller


def set_poller(poller: Poller):
    global _default_poller
    _default_poller = poller
