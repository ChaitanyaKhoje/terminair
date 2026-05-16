"""Tests for config loading and credential handling."""

from pathlib import Path

import pytest

from terminair.config import (
    CLIConfig,
    Config,
    Connection,
    ConnectionAuthBasic,
    DbtConfig,
    Settings,
    SnowflakeConfig,
    merge_configs,
)


def test_merge_config_with_basic_auth():
    file_config = Config()
    cli_config = CLIConfig(url="http://localhost:8080", user="admin", password="secret")
    result = merge_configs(file_config, cli_config)
    conn = result.connections["default"]
    assert conn.auth.username == "admin"
    assert conn.auth.password == "secret"


def test_merge_config_url_without_creds_raises():
    """Providing --url without --user/--password should raise, not silently send empty token."""
    file_config = Config()
    cli_config = CLIConfig(url="http://localhost:8080")
    with pytest.raises(ValueError, match="credentials"):
        merge_configs(file_config, cli_config)


def test_settings_has_no_from_env():
    """from_env was dead code referencing nonexistent api_token field — verify it's removed."""
    assert not hasattr(Settings, "from_env")


def test_connection_supports_optional_dbt_and_snowflake():
    conn = Connection(
        url="http://localhost:8080",
        auth=ConnectionAuthBasic(username="admin", password="secret"),
        dbt=DbtConfig(
            manifest_path=Path("/tmp/manifest.json"),
            run_results_path=Path("/tmp/run_results.json"),
            dag_names=["finance"],
        ),
        snowflake=SnowflakeConfig(
            account="acct",
            user="user",
            password="pw",
            warehouse="wh",
            database="db",
            role="role",
        ),
    )

    assert conn.dbt is not None
    assert conn.dbt.manifest_path == Path("/tmp/manifest.json")
    assert conn.snowflake is not None
    assert conn.snowflake.account == "acct"


def test_merge_config_overrides_dbt_paths_and_appends_dags():
    file_config = Config(
        connections={
            "default": Connection(
                url="http://localhost:8080",
                auth=ConnectionAuthBasic(username="admin", password="secret"),
                dbt=DbtConfig(
                    manifest_path=Path("/file/manifest.json"),
                    run_results_path=Path("/file/run_results.json"),
                    dag_names=["existing"],
                ),
            )
        },
        settings=Settings(default_connection="default"),
    )
    cli_config = CLIConfig(
        manifest_path=Path("/cli/manifest.json"),
        run_results_path=Path("/cli/run_results.json"),
        dag_names=["finance", "marketing"],
    )

    result = merge_configs(file_config, cli_config)
    conn = result.connections["default"]
    assert conn.dbt is not None
    assert conn.dbt.manifest_path == Path("/cli/manifest.json")
    assert conn.dbt.run_results_path == Path("/cli/run_results.json")
    assert conn.dbt.dag_names == ["existing", "finance", "marketing"]


def test_merge_config_demo_mode_skips_connection_requirements():
    file_config = Config()
    cli_config = CLIConfig(demo=True, dag_names=["finance"])

    result = merge_configs(file_config, cli_config)

    assert result.connections == {}
    assert result.settings.default_connection == "default"
