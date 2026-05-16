# ruff: noqa: UP042
"""Data classes for the dbt model intelligence data layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ModelState:
    # Required fields (no default)
    node_id: str
    name: str
    tag: str
    status: str  # running | success | failed | queued | skipped
    dag_id: str
    task_id: str
    materialization: str
    schema_name: str
    database_name: str
    has_upstream_failure: bool

    # Optional scalar fields
    duration_s: float | None = None
    rows_written: int | None = None
    rows_previous: int | None = None
    row_delta_pct: float | None = None
    bytes_scanned: int | None = None
    pod_name: str | None = None
    warehouse: str | None = None
    error_message: str | None = None
    run_started_at: str | None = None
    run_finished_at: str | None = None

    # compiled_sql is populated from the manifest JSON key "compiled_code"
    compiled_sql: str | None = None

    # Collection fields
    all_tags: list[str] = field(default_factory=list)
    upstream_deps: list[str] = field(default_factory=list)
    downstream_deps: list[str] = field(default_factory=list)
    grain_columns: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    # Dict fields
    upstream_statuses: dict[str, str] = field(default_factory=dict)
    dbt_vars: dict[str, str] = field(default_factory=dict)
    config_block: dict = field(default_factory=dict)


@dataclass
class RegressionSignal:
    node_id: str
    name: str
    signal_type: str  # row_drop | row_spike | grain_added | grain_removed | upstream_schema_change | new_model_no_baseline
    severity: str     # warning | critical | info
    description: str
    row_delta_pct: float | None = None
    grain_before: list[str] = field(default_factory=list)
    grain_after: list[str] = field(default_factory=list)
    detail: str = ""


__all__ = ["ModelState", "RegressionSignal", "Severity"]
