"""Test that event log loader uses correct model field names."""

from datetime import datetime

from terminair.api.models import EventLog


def test_event_log_model_fields():
    """Verify the EventLog model uses event_timestamp and event_type, not when/event."""
    log = EventLog(
        event_log_id=1,
        event_timestamp=datetime(2026, 4, 13, 12, 0, 0),
        event_type="dag_started",
        dag_id="test_dag",
        owner="admin",
    )
    assert log.event_timestamp == datetime(2026, 4, 13, 12, 0, 0)
    assert log.event_type == "dag_started"
    assert not hasattr(log, "when")
    assert not hasattr(log, "event")
