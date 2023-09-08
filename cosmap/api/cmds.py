import json
from pathlib import Path

import toml
from loguru import logger

from cosmap.analysis import manage
from cosmap.analysis.utils import build_analysis_object


def install_analysis(analysis_path: Path, overwrite=False, name=None):
    manage.install_analysis(analysis_path, name)


def uninstall_analysis(name: str):
    manage.uninstall_analysis(name)
    print(f'Analysis "{name}" uninstalled successfully')


def run_analysis(analysis_path: Path):
    if analysis_path.suffix == ".json":
        with open(analysis_path, "r") as f:
            config = json.load(f)
    elif analysis_path.suffix == ".toml":
        config = toml.load(analysis_path)
    else:
        raise ValueError(
            f"Could not parse the analysis config {analysis_path}: expect"
            "a toml or json file"
        )
    try:
        base_analysis = config["base-analysis"]
    except KeyError:
        raise KeyError(
            f"Could not find a base analysis in the config " f"file {analysis_path}"
        )

    if (amod := (config.get("analysis-mod", None))) is not None:
        logger.info(f"Running analysis `{base_analysis}` with variant `{amod}`")
    else:
        logger.info(f"Running analysis {base_analysis}")
    logger.info(f"Loading analysis files for {base_analysis}")
    analysis_data = manage.load_analysis_files(base_analysis, amod)
    logger.info(f"Preparing analysis {analysis_path.stem}")
    analysis_object = build_analysis_object(analysis_data, config)
    logger.info(f"Running analysis {analysis_path.stem} ")
    analysis_object.run()


def list_analyses():
    model_names = list(manage.get_known_analyses().keys())
    if not model_names:
        print("No analyses installed")
        return
    output = "\n".join(model_names)
    print("\033[1mKNOWN ANALYSES:\033[0m\n")
    print(output)
    print("\n")


def locate_analysis(name: str):
    """
    Return the location of the analysis definition on disk.
    """
    return manage.get_analysis_path(name)
