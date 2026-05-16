# ruff: noqa: UP042
"""Pydantic models mapping to Airflow REST API responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DagRunState(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    QUEUED = "queued"

    def __str__(self):
        return self.value


class TaskState(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    QUEUED = "queued"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    REMOVED = "removed"
    DEFERRED = "deferred"

    def __str__(self):
        return self.value


class DagTag(BaseModel):
    name: str


class SchedulerHealth(BaseModel):
    status: str
    latest_scheduler_heartbeat: str | None = None


class MetadbHealth(BaseModel):
    status: str


class HealthInfo(BaseModel):
    metadatabase: MetadbHealth
    scheduler: SchedulerHealth


class Pool(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    slots: int = 0
    # Some Airflow versions/hosts omit these fields; provide safe defaults
    used_slots: int = 0
    queued_slots: int = 0
    running_slots: int = Field(default=0, alias="running_slots")
    open_slots: int = Field(default=0, alias="open_slots")


class PoolList(BaseModel):
    pools: list[Pool]


class Dag(BaseModel):
    dag_id: str
    description: str | None = None
    owners: list[str]
    is_paused: bool
    is_active: bool = True
    schedule_interval: str | None = None
    timetable_description: str | None = None
    next_dagrun: str | None = None
    tags: list[DagTag] = []
    file_token: str | None = None

    def __init__(self, **data):
        # Handle schedule_interval as dict (Airflow 2.10+)
        if isinstance(data.get("schedule_interval"), dict):
            data["schedule_interval"] = data["schedule_interval"].get("value")
        super().__init__(**data)


class DagList(BaseModel):
    dags: list[Dag]
    total_entries: int | None = None


class DagRun(BaseModel):
    dag_run_id: str
    dag_id: str
    execution_date: datetime
    start_date: datetime | None = None
    end_date: datetime | None = None
    state: DagRunState
    run_type: str
    external_trigger: bool
    conf: dict | None = None
    note: str | None = None


class DagRunList(BaseModel):
    dag_runs: list[DagRun]
    total_entries: int | None = None


class SlaMiss(BaseModel):
    task_id: str
    dag_id: str
    execution_date: datetime | None = None
    email_sent: bool = False
    timestamp: datetime | None = None
    description: str | None = None
    notification_sent: bool = False


class TaskInstance(BaseModel):
    task_id: str
    dag_id: str
    dag_run_id: str = Field(alias="run_id")
    execution_date: datetime
    start_date: datetime | None = None
    end_date: datetime | None = None
    queued_when: datetime | None = None
    duration: float | None = None
    state: TaskState | None = None
    try_number: int
    max_tries: int
    operator: str
    queue: str | None = None
    pool: str
    priority_weight: int
    sla_miss: SlaMiss | None = None

    model_config = ConfigDict(populate_by_name=True)


class TaskInstanceList(BaseModel):
    task_instances: list[TaskInstance]


class ImportError(BaseModel):
    filename: str
    timestamp: datetime | None = None
    stack_trace: str


class ImportErrorList(BaseModel):
    import_errors: list[ImportError]


class ConfigValue(BaseModel):
    key: str
    value: str | None = None


class LogResponse(BaseModel):
    content: str


class EventLog(BaseModel):
    event_log_id: int
    event_timestamp: datetime | None = None
    event_type: str
    task_id: str | None = None
    dag_id: str | None = None
    run_id: str | None = None
    owner: str | None = None
    extra: str | None = None


class EventLogList(BaseModel):
    event_logs: list[EventLog]


class DAGDetailsTask(BaseModel):
    id: str
    label: str
    depends_on_past: bool = False
    wait_for_downstream: bool = False
    executor: str | None = None
    pool: str | None = None
    queue: str | None = None
    priority_weight: int | None = None
    operator: str
    retries: int | None = None
    retry_delay_seconds: int | None = None
    max_retry_delay_seconds: int | None = None
    ui_color: str | None = None
    ui_fgcolor: str | None = None
    upstream_task_ids: list[str] = Field(default_factory=list)


class DAGDetails(BaseModel):
    dag_id: str
    dag_display_name: str
    description: str | None = None
    schedule_interval: str | None = None
    timetable_description: str | None = None
    tags: list[str] = []
    owner: str | None = None
    default_view: str | None = None
    tasks: list[DAGDetailsTask] = []


class DAGTask(BaseModel):
    task_id: str
    downstream_task_ids: list[str] = Field(default_factory=list)


class DAGTaskList(BaseModel):
    tasks: list[DAGTask] = []
    total_entries: int = 0


class XComEntry(BaseModel):
    key: str
    task_id: str
    dag_id: str
    dag_run_id: str = Field(alias="run_id", default="")
    execution_date: datetime | None = None
    timestamp: datetime | None = None
    value: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class XComEntryList(BaseModel):
    xcom_entries: list[XComEntry] = []
    total_entries: int = 0


class SlaMissItem(BaseModel):
    dag_id: str
    task_id: str
    execution_date: datetime | None = None
    email_sent: bool = False
    timestamp: datetime | None = None
    description: str | None = None


class SlaMissList(BaseModel):
    sla_miss: list[SlaMissItem] = []
    total_entries: int = 0


class Dataset(BaseModel):
    id: str
    uri: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DatasetList(BaseModel):
    datasets: list[Dataset]
    total_entries: int | None = None


class DatasetEvent(BaseModel):
    id: int
    dataset_id: str
    dataset_uri: str
    created_at: datetime
    source_dag_id: str | None = None
    source_task_id: str | None = None
    source_run_id: str | None = None


class DatasetEventList(BaseModel):
    dataset_events: list[DatasetEvent]
    total_entries: int | None = None
