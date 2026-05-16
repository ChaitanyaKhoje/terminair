# ruff: noqa: UP045, UP007
"""Configuration loading, validation, and env var expansion."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field


class ConnectionAuthBasic(BaseModel):
    type: Literal["basic"] = "basic"
    username: str
    password: str


class ConnectionAuthToken(BaseModel):
    type: Literal["token"] = "token"
    token: str


class DbtConfig(BaseModel):
    manifest_path: Optional[Path] = None
    run_results_path: Optional[Path] = None
    run_results_previous_path: Optional[Path] = None
    manifest_previous_path: Optional[Path] = None
    dag_names: list[str] = Field(default_factory=list)


class SnowflakeConfig(BaseModel):
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    role: str


class Connection(BaseModel):
    url: str
    auth: Annotated[
        Union[ConnectionAuthBasic, ConnectionAuthToken],
        Field(discriminator="type"),
    ]
    dbt: Optional[DbtConfig] = None
    snowflake: Optional[SnowflakeConfig] = None


class Settings(BaseModel):
    default_connection: str = "default"
    refresh_interval: int = 60
    log_poll_interval: int = 2
    default_dag_run_limit: int = 50
    theme: str = "dark"
    confirm_actions: bool = True
    timestamp_format: str = "relative"
    watchlist: list = []
    show_sensitive: bool = False



class Config(BaseModel):
    connections: dict[str, Connection] = Field(default_factory=dict)
    settings: Settings = Settings()
    keybindings: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Config:
        if path is None:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                path = Path(xdg_config) / "terminair" / "config.yaml"
            else:
                path = Path.home() / ".terminair" / "config.yaml"

        if not path.exists():
            return cls()

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        expanded = cls._expand_env_vars(raw)
        settings = expanded.setdefault("settings", {})
        if "show_sensitive" not in settings:
            env_sensitive = os.environ.get("TERMINAIR_SHOW_SENSITIVE", "").strip().lower()
            settings["show_sensitive"] = env_sensitive in {"1", "true", "yes", "on"}
        return cls(**expanded)

    @classmethod
    def _expand_env_vars(cls, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = cls._expand_env_vars(value)
            elif isinstance(value, list):
                expanded_list = []
                for item in value:
                    if isinstance(item, dict):
                        expanded_list.append(cls._expand_env_vars(item))
                    elif isinstance(item, list):
                        expanded_list.append(cls._expand_env_vars({"_": item})["_"])
                    elif isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                        env_var = item[2:-1]
                        expanded_list.append(os.environ.get(env_var, item))
                    else:
                        expanded_list.append(item)
                result[key] = expanded_list
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                result[key] = os.environ.get(env_var, value)
            else:
                result[key] = value
        return result


class CLIConfig(BaseModel):
    url: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    ctx: Optional[str] = None
    config_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    run_results_path: Optional[Path] = None
    dag_names: list[str] = Field(default_factory=list)
    demo: bool = False
    refresh: Optional[int] = None
    version: bool = False
    help: bool = Field(default=False, alias="help")


def _copy_connection(connection: Connection) -> Connection:
    return connection.model_copy(deep=True)


def _merge_dbt_config(
    base: Optional[DbtConfig],
    cli_config: CLIConfig,
) -> Optional[DbtConfig]:
    merged = base.model_copy(deep=True) if base is not None else DbtConfig()

    if cli_config.manifest_path is not None:
        merged.manifest_path = cli_config.manifest_path
    if cli_config.run_results_path is not None:
        merged.run_results_path = cli_config.run_results_path
    if cli_config.dag_names:
        merged.dag_names.extend(cli_config.dag_names)

    return merged


def merge_configs(file_config: Config, cli_config: CLIConfig) -> Config:
    connections = {name: _copy_connection(conn) for name, conn in file_config.connections.items()}
    active_conn = cli_config.ctx or file_config.settings.default_connection

    if cli_config.demo:
        settings_dict = file_config.settings.model_dump()
        if cli_config.refresh is not None:
            settings_dict["refresh_interval"] = cli_config.refresh
        settings_dict["default_connection"] = active_conn
        return Config(
            connections=connections,
            settings=Settings(**settings_dict),
            keybindings=file_config.keybindings,
        )

    if cli_config.url:
        conn_name = cli_config.ctx or "default"
        base_conn = connections.get(conn_name)
        if cli_config.user and cli_config.password:
            merged_conn = base_conn.model_copy(deep=True) if base_conn is not None else None
            if merged_conn is None:
                merged_conn = Connection(
                    url=cli_config.url,
                    auth=ConnectionAuthBasic(
                        type="basic",
                        username=cli_config.user,
                        password=cli_config.password,
                    ),
                )
            else:
                merged_conn.url = cli_config.url
                merged_conn.auth = ConnectionAuthBasic(
                    type="basic",
                    username=cli_config.user,
                    password=cli_config.password,
                )
            connections[conn_name] = merged_conn
        else:
            raise ValueError(
                "URL provided without credentials. Use --user/--password, "
                "set TERMINAIR_PASSWORD env var, or configure a connection in config.yaml."
            )

    if active_conn not in connections:
        raise ValueError(f"Connection '{active_conn}' not found")

    active_connection = connections[active_conn]
    active_connection.dbt = _merge_dbt_config(active_connection.dbt, cli_config)

    settings_dict = file_config.settings.model_dump()
    if cli_config.refresh is not None:
        settings_dict["refresh_interval"] = cli_config.refresh
    settings_dict["default_connection"] = active_conn

    return Config(
        connections=connections,
        settings=Settings(**settings_dict),
        keybindings=file_config.keybindings,
    )
