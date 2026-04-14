"""Test fixtures for AirTerm."""

import pytest


@pytest.fixture
def test_config():
    from airterm.config import Config, Connection, ConnectionAuthBasic, Settings

    return Config(
        connections={
            "test": Connection(
                url="http://localhost:8080/api/v1",
                auth=ConnectionAuthBasic(
                    type="basic",
                    username="admin",
                    password="admin",
                ),
            )
        },
        settings=Settings(default_connection="test"),
    )


@pytest.fixture
def mock_dags():
    return {
        "dags": [
            {
                "dag_id": "daily_orders",
                "description": "Daily orders ETL",
                "owners": ["data-team"],
                "is_paused": False,
                "is_active": True,
                "schedule_interval": "0 0 * * *",
                "timetable_description": "Daily at midnight",
                "next_dagrun": "2026-04-14T00:00:00+00:00",
                "tags": [],
            }
        ]
    }


@pytest.fixture
def mock_dag_runs():
    return {
        "dag_runs": [
            {
                "dag_run_id": "scheduled__2026_04_13",
                "dag_id": "daily_orders",
                "execution_date": "2026-04-13T00:00:00+00:00",
                "start_date": "2026-04-13T00:00:01+00:00",
                "end_date": "2026-04-13T00:10:00+00:00",
                "state": "success",
                "run_type": "scheduled",
                "external_trigger": False,
                "conf": None,
            }
        ]
    }
