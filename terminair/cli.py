"""CLI entrypoint for Terminair."""

import os
from pathlib import Path

import click

from terminair.app import TerminairApp
from terminair.config import CLIConfig, Config, merge_configs


@click.command()
@click.option("--url", help="Airflow API URL")
@click.option("--user", help="Username for basic auth")
@click.option("--password", help="Password for basic auth (prefer TERMINAIR_PASSWORD env var)")
@click.option("--ctx", help="Connection context name")
@click.option("--config", type=click.Path(path_type=Path), help="Config file path")
@click.option(
    "--manifest",
    type=click.Path(path_type=Path),
    help="Override the dbt manifest path",
)
@click.option(
    "--run-results",
    type=click.Path(path_type=Path),
    help="Override the dbt run_results path",
)
@click.option(
    "--dag",
    multiple=True,
    help="Append a DAG name to the dbt configuration (repeatable)",
)
@click.option("--demo", is_flag=True, help="Run against demo data with no external services")
@click.option(
    "--refresh",
    type=int,
    help="Live auto-refresh interval in seconds (default: 60; maps to refresh_interval in config)",
)
@click.option("--version", is_flag=True, help="Show version")
def main(
    url,
    user,
    password,
    ctx,
    config,
    manifest,
    run_results,
    dag,
    demo,
    refresh,
    version,
):
    """Terminair - A k9s-style TUI for Apache Airflow."""
    if version:
        try:
            from importlib.metadata import version as pkg_version
            ver = pkg_version("terminair")
        except Exception:
            ver = "1.0.0"
        click.echo(f"terminair version {ver}")
        return

    # Resolve password: CLI arg > env var > interactive prompt
    if url and user and not password:
        password = os.environ.get("TERMINAIR_PASSWORD")
        if not password:
            password = click.prompt("Password", hide_input=True)

    cli_config = CLIConfig(
        url=url,
        user=user,
        password=password,
        ctx=ctx,
        config_path=config,
        manifest_path=manifest,
        run_results_path=run_results,
        dag_names=list(dag),
        demo=demo,
        refresh=refresh,
    )

    file_config = Config.load(cli_config.config_path)

    try:
        full_config = merge_configs(file_config, cli_config)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    app = TerminairApp(full_config, demo_mode=cli_config.demo)
    app.run()


if __name__ == "__main__":
    main()
