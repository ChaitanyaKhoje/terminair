"""Smoke tests for the dbt screen stack and packaging targets."""

from __future__ import annotations

from pathlib import Path

from terminair.config import Config


def test_app_registers_dbt_screens():
    from terminair.app import TerminairApp
    from terminair.screens import LineageScreen, ModelDetailScreen, ModelListScreen, ProblemsScreen

    app = TerminairApp(Config(), demo_mode=True)

    assert app.SCREENS["model_list"] is ModelListScreen
    assert app.SCREENS["problems"] is ProblemsScreen
    assert app.SCREENS["lineage"] is LineageScreen
    assert app.SCREENS["detail"] is ModelDetailScreen


def test_makefile_has_dbt_targets():
    makefile = Path("Makefile").read_text()

    assert "dbt-demo" in makefile
    assert "dbt-dev" in makefile


def test_dockerfile_exists_and_exposes_airflow_url():
    dockerfile = Path("Dockerfile").read_text()

    assert "AIRFLOW_URL" in dockerfile
    assert "python:3.11-slim" in dockerfile

