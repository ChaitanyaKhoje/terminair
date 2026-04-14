"""Reactive state container for AirTerm."""

from typing import Optional

from textual.app import App
from textual.reactive import reactive

from airterm.api import models


class StateManager(App):
    """Reactive state container. Textual widgets observe changes."""

    dags = reactive(list[models.Dag]([]))
    dag_runs = reactive(dict[str, list[models.DagRun]]({}))
    task_instances = reactive(dict[str, list[models.TaskInstance]]({}))
    pools = reactive(list[models.Pool]([]))
    health = reactive[Optional[models.HealthInfo]](None)
    active_connection = reactive[str]("default")
    last_error = reactive[Optional[str]](None)
    connection_latency_ms = reactive[float](0.0)
    active_dag_id = reactive[Optional[str]](None)
    active_run_id = reactive[Optional[str]](None)
    active_task_id = reactive[Optional[str]](None)

    loading = reactive[bool](False)
    error_message = reactive[Optional[str]](None)


_state_instance: Optional[StateManager] = None


def get_state() -> StateManager:
    global _state_instance
    if _state_instance is None:
        _state_instance = StateManager()
    return _state_instance
