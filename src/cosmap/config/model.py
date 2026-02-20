import json
import sys
from importlib import import_module
from pathlib import Path

import toml
from pydantic import BaseModel

from cosmap import locations
from cosmap.analysis.dependencies import build_dependency_graph


class CosmapParameterModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class CosmapModelException(Exception):
    pass


def write_models(models: dict):
    output_file = locations.COSMAP_CONFIG_LOCATION / "known_models.json"
    with open(output_file, "w") as f:
        json.dump(models, f)


def verify_model(folder_path, module, model):
    transfromation_config = folder_path / "transformations.toml"
    with open(transfromation_config, "r") as f:
        transformations = toml.load(f)

    for tblock, transformations_ in transformations.items():
        if not tblock[0].isupper():
            continue
        try:
            block = getattr(module, tblock)
        except AttributeError:
            raise CosmapModelException(
                f"Could not find the implementation of block {tblock} in"
                f" the analysis {model.__name__}"
            )
        for name, transformation in transformations_.items():
            if not hasattr(block, name):
                raise CosmapModelException(
                    f"Could not find the transformation {name}"
                    f" in the model {model.__name__}"
                )

        verify_transformation_block(transformations_)


def verify_transformation_block(transformation_block: dict):
    """
    Verifies that a set of transformations are valid. This means
    that there are no cyclic dependencies, among other things.
    """
    build_dependency_graph(transformation_block)


def get_transformations(analysis_name: str) -> dict:
    """
    Returns the transformations for a given analysis.
    """
    known_models = get_known_models()
    if analysis_name not in known_models:
        raise CosmapModelException(f"Model '{analysis_name}' not found...")
    model_directory = Path(known_models[analysis_name]["path"])
    transformations_file = model_directory / "transformations.toml"
    if not transformations_file.exists():
        raise CosmapModelException(
            f"Could not find the transformations config file {transformations_file}"
        )
    with open(transformations_file, "r") as f:
        transformations = toml.load(f)
    return transformations


def get_known_models():
    expected_file = locations.COSMAP_CONFIG_LOCATION / "known_models.json"
    if not expected_file.exists():
        return {}
    else:
        with open(expected_file, "r") as f:
            data = json.load(f)
    return data


def add_new_model(model_file: Path, model_name: str):
    model_data = get_known_models()
    model_data.update(
        {
            model_name: {
                "path": str(model_file.parents[0]),
                "module_name": model_file.stem,
            }
        }
    )
    write_models(model_data)


def get_model(model_name: str):
    mod = get_definition_module(model_name)
    model = getattr(mod["module"], f"{model_name}Parameters")
    return model


def get_definition_module(model_name: str):
    known_models = get_known_models()
    if model_name not in known_models:
        raise CosmapModelException(f"Model '{model_name}' not found...")
    model_directory = known_models[model_name]["path"]
    module_name = known_models[model_name]["module_name"]
    module_path = Path(model_directory) / f"{module_name}.py"
    if not Path(module_path).exists():
        raise FileNotFoundError(f"Could not find definition file {str(module_path)}")
    if model_directory not in sys.path:
        sys.path.append(model_directory)
    mod = import_module(module_name)
    return {"path": module_path, "module": mod}


def get_model_path(model_name: str):
    models = get_known_models()
    if model_name not in models:
        raise CosmapModelException(f"Model '{model_name}' not found...")
    return models[model_name]["path"]
