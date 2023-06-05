from pathlib import Path
from cosmap.config.models import model
from cosmap.config.block import create_parameter_block, create_analysis_block
from cosmap.analysis.analysis import CosmapAnalysis
from cosmap.analysis.utils import build_analysis_object
from cosmap.config.models.model import get_known_models
import toml
import json

def install_analysis(analysis_path: Path, overwrite = False, name = None):
    if not Path.exists(analysis_path):
        raise FileNotFoundError(f"Could not find the analysis path {analysis_path}")
    if not analysis_path.name.endswith(".py"):
        raise ValueError(f"Expected a python file for the analysis but found {Path.name}")
    
    if name is None:
        name = analysis_path.stem
    analysis_path = Path.cwd() / analysis_path
    model.install_analysis(analysis_path, name, overwrite = overwrite)
    print(f"Analysis \"{name}\" installed successfully")

def run_analysis(analysis_path: Path):
    if analysis_path.suffix == ".json":
        with open(analysis_path, "r") as f:
            config = json.load(f)
    elif analysis_path.suffix == ".toml":
        config = toml.load(analysis_path)
    else:
        raise ValueError(f"Could not parse the analysis config {analysis_path}: expect a toml or json file")
    try:
        base_analysis = config["base-analysis"]
    except KeyError:
        raise KeyError(f"Could not find a base analysis in the config file {analysis_path}")
    

    analysis_object = build_analysis_object(base_analysis, config)
    analysis_object.run()


def list_analyses():
    model_names = list(get_known_models().keys())
    output = "\n".join(model_names)
    print("\033[1mKNOWN ANALYSES:\033[0m\n")
    print(output)
    print("\n")
