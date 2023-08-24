from pathlib import Path

import click

from cosmap.api import cmds


@click.group()
def cli():
    pass


@click.command(name="install")
@click.argument("path", type=click.Path())
@click.option(
    "-n",
    "--name",
    type=click.STRING,
    required=False,
    help="The name of the analysis. If not provided, will be inffered from the path",
)
@click.option(
    "--overwrite", "-o", is_flag=True, help="Overwrite the model if it already exists"
)
def install_analysis(path: Path, overwrite: bool = False, name=None):
    """
    Install a new analysis.
    The path should point to a python file where the analysis configuation is defined.
    """
    try:
        p = Path(path).resolve()
    except ValueError:
        raise ValueError(f"Could not parse the path {path}")
    cmds.install_analysis(p, overwrite=overwrite, name=name)


@click.command(name="uninstall")
@click.argument("name", type=click.STRING)
def uninstall_analysis(name: str):
    """
    Uninstall an analysis by name.
    """
    cmds.uninstall_analysis(name)


@click.command(name="run")
@click.argument("analysis_config", type=click.Path())
def run(analysis_config: Path):
    """
    Run a given analysis. The analysis config should be a json or toml file.
    """
    try:
        p = Path(analysis_config)
    except ValueError:
        raise ValueError(f"Could not parse the path {analysis_config}")
    if not p.exists():
        raise FileNotFoundError(
            f"Could not find the analysis config at {analysis_config}"
        )
    cmds.run_analysis(p)


@click.command(name="list")
def list_installed_analyses():
    """
    List currently installed analyses.
    """
    cmds.list_analyses()


@click.command(name="locate")
@click.argument("name", type=click.STRING)
def locate_analysis(name: str):
    """
    Return the location of the analysis definition on disk.
    """
    path = cmds.locate_analysis(name)
    print(path)


cli.add_command(install_analysis)
cli.add_command(uninstall_analysis)
cli.add_command(run)
cli.add_command(list_installed_analyses)
cli.add_command(locate_analysis)

if __name__ == "__main__":
    cli()
