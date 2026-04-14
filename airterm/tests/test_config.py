"""Tests for config loading and credential handling."""

import pytest

from airterm.config import CLIConfig, Config, Settings, merge_configs


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
