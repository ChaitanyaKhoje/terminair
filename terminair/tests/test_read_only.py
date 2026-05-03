"""Tests to enforce read-only contract."""



def test_client_has_no_write_methods():
    """Enforce read only contract at the type level."""
    from terminair.api.client import AirflowClient

    write_methods = [
        "trigger_dag",
        "clear_task",
        "toggle_dag",
        "mark_task",
        "post",
        "patch",
        "delete",
    ]

    for method in write_methods:
        assert not hasattr(AirflowClient, method), f"Client should not have write method: {method}"
