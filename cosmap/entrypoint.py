import click
from pathlib import Path
from cosmap.api import cmds

@click.group()
def cli():
    pass



@click.command(name="install")
@click.argument("path", type = click.Path())
@click.option( "-n", "--name", type = click.STRING, required = False)
@click.option("--overwrite", "-o", is_flag = True, help = "Overwrite the model if it already exists")
def install_analysis(path: Path, overwrite: bool = False, name = None):
    try:
        p  = Path(path)
    except ValueError:
        raise ValueError(f"Could not parse the path {path}")
    cmds.install_analysis(p, overwrite = overwrite, name = name)

cli.add_command(install_analysis)

@click.command(name="run")
@click.argument("analysis_config", type = click.Path())
def run(analysis_config: Path):
    try:
        p  = Path(analysis_config)
    except ValueError:
        raise ValueError(f"Could not parse the path {analysis_config}")
    if not p.exists():
        raise FileNotFoundError(f"Could not find the analysis config at {analysis_config}")
    cmds.run_analysis(p)

cli.add_command(run)

@click.command(name="list")
def list_installed_analyses():
    cmds.list_analyses()

cli.add_command(list_installed_analyses)

if __name__ == "__main__":
    cli()