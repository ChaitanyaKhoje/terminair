"""Background poller for Airflow API data."""

import asyncio
from typing import Callable, Optional

from airterm.api.client import AirflowClient


class Poller:
    """Background poller for Airflow API data."""

    def __init__(self, client: AirflowClient):
        self._client = client
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def start_polling(
        self,
        resource: str,
        interval: float,
        callback: Optional[Callable] = None,
        **params,
    ):
        """Start polling a resource. Replaces existing poll for same resource."""
        await self.stop_polling(resource)
        self._running = True
        task = asyncio.create_task(self._poll_loop(resource, interval, callback, **params))
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
        callback: Optional[Callable],
        **params,
    ):
        while self._running:
            try:
                data = await self._poll_once(resource, **params)
                if callback and data is not None:
                    callback(data)
            except Exception:
                pass  # Flash will be handled by the app-level refresh
            await asyncio.sleep(interval)

    async def _poll_once(self, resource: str, **params):
        if resource == "dags":
            return await self._client.get_dags(**params)
        elif resource == "pools":
            return await self._client.get_pools()
        elif resource == "health":
            return await self._client.get_health()
        return None


_default_poller: Optional[Poller] = None


def get_poller() -> Optional[Poller]:
    return _default_poller


def set_poller(poller: Poller):
    global _default_poller
    _default_poller = poller
