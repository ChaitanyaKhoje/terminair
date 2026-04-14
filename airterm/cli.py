"""CLI entrypoint for AirTerm."""

from pathlib import Path

import click

from airterm.app import AirTermApp
from airterm.config import CLIConfig, Config, merge_configs


@click.command()
@click.option("--url", help="Airflow API URL")
@click.option("--user", help="Username for basic auth")
@click.option("--password", help="Password for basic auth")
@click.option("--ctx", help="Connection context name")
@click.option("--config", type=click.Path(path_type=Path), help="Config file path")
@click.option("--dag", help="Jump to specific DAG on startup")
@click.option("--refresh", type=int, help="Refresh interval in seconds")
@click.option("--version", is_flag=True, help="Show version")
def main(
    url,
    user,
    password,
    ctx,
    config,
    dag,
    refresh,
    version,
):
    """AirTerm - A k9s-style TUI for Apache Airflow."""
    if version:
        click.echo("airterm version 0.1.0")
        return

    cli_config = CLIConfig(
        url=url,
        user=user,
        password=password,
        ctx=ctx,
        config_path=config,
        dag=dag,
        refresh=refresh,
    )

    file_config = Config.load(cli_config.config_path)

    try:
        full_config = merge_configs(file_config, cli_config)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    app = AirTermApp(full_config)
    app.run()


if __name__ == "__main__":
    main()
