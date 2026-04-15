"""Pydantic models mapping to Airflow REST API responses."""

from datetime import datetime
from enum import Enum
from typing import Optional

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
    latest_scheduler_heartbeat: Optional[str] = None


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
    description: Optional[str] = None
    owners: list[str]
    is_paused: bool
    is_active: bool = True
    schedule_interval: Optional[str] = None
    timetable_description: Optional[str] = None
    next_dagrun: Optional[str] = None
    tags: list[DagTag] = []
    file_token: Optional[str] = None

    def __init__(self, **data):
        # Handle schedule_interval as dict (Airflow 2.10+)
        if isinstance(data.get("schedule_interval"), dict):
            data["schedule_interval"] = data["schedule_interval"].get("value")
        super().__init__(**data)


class DagList(BaseModel):
    dags: list[Dag]
    total_entries: Optional[int] = None


class DagRun(BaseModel):
    dag_run_id: str
    dag_id: str
    execution_date: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    state: DagRunState
    run_type: str
    external_trigger: bool
    conf: Optional[dict] = None
    note: Optional[str] = None


class DagRunList(BaseModel):
    dag_runs: list[DagRun]
    total_entries: Optional[int] = None


class SlaMiss(BaseModel):
    task_id: str
    dag_id: str
    execution_date: Optional[datetime] = None
    email_sent: bool = False
    timestamp: Optional[datetime] = None
    description: Optional[str] = None
    notification_sent: bool = False


class TaskInstance(BaseModel):
    task_id: str
    dag_id: str
    dag_run_id: str = Field(alias="run_id")
    execution_date: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    queued_when: Optional[datetime] = None
    duration: Optional[float] = None
    state: Optional[TaskState] = None
    try_number: int
    max_tries: int
    operator: str
    queue: Optional[str] = None
    pool: str
    priority_weight: int
    sla_miss: Optional[SlaMiss] = None

    model_config = ConfigDict(populate_by_name=True)


class TaskInstanceList(BaseModel):
    task_instances: list[TaskInstance]


class ImportError(BaseModel):
    filename: str
    timestamp: Optional[datetime] = None
    stack_trace: str


class ImportErrorList(BaseModel):
    import_errors: list[ImportError]


class ConfigValue(BaseModel):
    key: str
    value: Optional[str] = None


class LogResponse(BaseModel):
    content: str


class EventLog(BaseModel):
    event_log_id: int
    event_timestamp: Optional[datetime] = None
    event_type: str
    task_id: Optional[str] = None
    dag_id: Optional[str] = None
    run_id: Optional[str] = None
    owner: Optional[str] = None
    extra: Optional[str] = None


class EventLogList(BaseModel):
    event_logs: list[EventLog]


class DAGDetailsTask(BaseModel):
    id: str
    label: str
    depends_on_past: bool = False
    wait_for_downstream: bool = False
    executor: Optional[str] = None
    pool: Optional[str] = None
    queue: Optional[str] = None
    priority_weight: Optional[int] = None
    operator: str
    retries: Optional[int] = None
    retry_delay_seconds: Optional[int] = None
    max_retry_delay_seconds: Optional[int] = None
    ui_color: Optional[str] = None
    ui_fgcolor: Optional[str] = None
    upstream_task_ids: list[str] = Field(default_factory=list)


class DAGDetails(BaseModel):
    dag_id: str
    dag_display_name: str
    description: Optional[str] = None
    schedule_interval: Optional[str] = None
    timetable_description: Optional[str] = None
    tags: list[str] = []
    owner: Optional[str] = None
    default_view: Optional[str] = None
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
    execution_date: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    value: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class XComEntryList(BaseModel):
    xcom_entries: list[XComEntry] = []
    total_entries: int = 0


class SlaMissItem(BaseModel):
    dag_id: str
    task_id: str
    execution_date: Optional[datetime] = None
    email_sent: bool = False
    timestamp: Optional[datetime] = None
    description: Optional[str] = None


class SlaMissList(BaseModel):
    sla_miss: list[SlaMissItem] = []
    total_entries: int = 0


class Dataset(BaseModel):
    id: str
    uri: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DatasetList(BaseModel):
    datasets: list[Dataset]
    total_entries: Optional[int] = None


class DatasetEvent(BaseModel):
    id: int
    dataset_id: str
    dataset_uri: str
    created_at: datetime
    source_dag_id: Optional[str] = None
    source_task_id: Optional[str] = None
    source_run_id: Optional[str] = None


class DatasetEventList(BaseModel):
    dataset_events: list[DatasetEvent]
    total_entries: Optional[int] = None
