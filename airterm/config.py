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


class Connection(BaseModel):
    url: str
    auth: Annotated[
        Union[ConnectionAuthBasic, ConnectionAuthToken],
        Field(discriminator="type"),
    ]


class Settings(BaseModel):
    default_connection: str = "default"
    refresh_interval: int = 60
    log_poll_interval: int = 2
    default_dag_run_limit: int = 50
    theme: str = "dark"
    confirm_actions: bool = True
    timestamp_format: str = "relative"
    watchlist: list = []



class Config(BaseModel):
    connections: dict[str, Connection] = {}
    settings: Settings = Settings()
    keybindings: dict[str, str] = {}

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Config:
        if path is None:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                path = Path(xdg_config) / "airterm" / "config.yaml"
            else:
                path = Path.home() / ".airterm" / "config.yaml"

        if not path.exists():
            return cls()

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        return cls(**cls._expand_env_vars(raw))

    @classmethod
    def _expand_env_vars(cls, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = cls._expand_env_vars(value)
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
    dag: Optional[str] = None
    refresh: Optional[int] = None
    version: bool = False
    help: bool = Field(default=False, alias="help")


def merge_configs(file_config: Config, cli_config: CLIConfig) -> Config:
    connections = dict(file_config.connections)

    if cli_config.url:
        conn_name = cli_config.ctx or "default"
        if cli_config.user and cli_config.password:
            connections[conn_name] = Connection(
                url=cli_config.url,
                auth=ConnectionAuthBasic(
                    type="basic",
                    username=cli_config.user,
                    password=cli_config.password,
                ),
            )
        else:
            raise ValueError(
                "URL provided without credentials. Use --user/--password, "
                "set AIRTERM_PASSWORD env var, or configure a connection in config.yaml."
            )

    active_conn = cli_config.ctx or file_config.settings.default_connection

    if active_conn not in connections:
        raise ValueError(f"Connection '{active_conn}' not found")

    settings_dict = file_config.settings.model_dump()
    if cli_config.refresh:
        settings_dict["refresh_interval"] = cli_config.refresh
    settings_dict["default_connection"] = active_conn

    return Config(
        connections=connections,
        settings=Settings(**settings_dict),
        keybindings=file_config.keybindings,
    )
