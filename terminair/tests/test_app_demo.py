"""Tests for demo-mode app bootstrap and data provider fallback."""

from __future__ import annotations

from terminair.config import Config


def test_demo_mode_uses_mock_data_provider():
    from terminair.app import TerminairApp
    from terminair.dbt.mock_data import MockDataProvider

    app = TerminairApp(Config(), demo_mode=True)
    provider = app.get_data_provider()

    assert isinstance(provider, MockDataProvider)


def test_missing_dbt_config_falls_back_to_mock_data_provider():
    from terminair.app import TerminairApp
    from terminair.dbt.mock_data import MockDataProvider

    app = TerminairApp(Config(), demo_mode=False)
    provider = app.get_data_provider()

    assert isinstance(provider, MockDataProvider)


def test_manifest_configured_but_missing_calls_flash_warn(tmp_path, monkeypatch):
    from terminair.app import TerminairApp
    from terminair.config import Connection, ConnectionAuthBasic, DbtConfig, Settings
    from terminair.dbt.mock_data import MockDataProvider

    file_config = Config(
        connections={
            "default": Connection(
                url="http://localhost:8080",
                auth=ConnectionAuthBasic(username="admin", password="secret"),
                dbt=DbtConfig(manifest_path=tmp_path / "nonexistent_manifest.json"),
            )
        },
        settings=Settings(default_connection="default"),
    )

    app = TerminairApp(file_config, demo_mode=False)

    flash_warn_calls: list[str] = []
    # monkeypatch must be applied before get_data_provider(), which calls _build_data_provider lazily
    monkeypatch.setattr(app, "_flash_warn", lambda text: flash_warn_calls.append(text))

    provider = app.get_data_provider()

    assert isinstance(provider, MockDataProvider)
    assert len(flash_warn_calls) == 1, f"Expected exactly 1 warn, got: {flash_warn_calls}"
    assert "missing" in flash_warn_calls[0].lower(), f"Unexpected message: {flash_warn_calls[0]}"
    assert "manifest" in flash_warn_calls[0].lower(), f"Unexpected message: {flash_warn_calls[0]}"

