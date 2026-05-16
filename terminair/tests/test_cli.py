"""Tests for CLI parsing and demo mode bootstrap."""

from __future__ import annotations

from click.testing import CliRunner


def test_cli_parses_repeatable_dag_and_demo(monkeypatch, tmp_path):
    from terminair.config import Config

    class DummyApp:
        last_config = None
        last_demo_mode = None
        ran = False

        def __init__(self, config, demo_mode=False):
            DummyApp.last_config = config
            DummyApp.last_demo_mode = demo_mode

        def run(self):
            DummyApp.ran = True

    monkeypatch.setattr("terminair.cli.Config.load", lambda path=None: Config())
    monkeypatch.setattr("terminair.cli.TerminairApp", DummyApp)

    manifest = tmp_path / "manifest.json"
    run_results = tmp_path / "run_results.json"
    manifest.write_text("{}")
    run_results.write_text("{}")

    runner = CliRunner()
    from terminair.cli import main

    result = runner.invoke(
        main,
        [
            "--demo",
            "--ctx",
            "demo",
            "--manifest",
            str(manifest),
            "--run-results",
            str(run_results),
            "--dag",
            "finance",
            "--dag",
            "marketing",
        ],
    )

    assert result.exit_code == 0, result.output
    assert DummyApp.ran is True
    assert DummyApp.last_demo_mode is True
    assert DummyApp.last_config is not None
    assert DummyApp.last_config.settings.default_connection == "demo"
    assert DummyApp.last_config.connections == {}
