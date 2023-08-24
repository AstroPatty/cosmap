from typing import List, TypeVar

from pydantic import BaseModel

from cosmap.config import models
from cosmap.config.analysis import AnalysisParameters


def parse_models(param_specification: dict) -> dict:
    """
    When needed inside a analysis specification file, models are specified
    with strings. We need to parse these into model objects. This
    function runs through the parameters and replaces strings that
    start with "model" with the appropriate model. It throws an error
    if it runs into a model it can't find.
    """
    new_spec = {}
    for key, value in param_specification.items():
        if isinstance(value, dict):
            new_spec[key] = parse_models(value)
        elif isinstance(value, str) and value.startswith(("models.", "extern.")):
            new_spec[key] = get_model(value)
        else:
            new_spec[key] = value
    return new_spec


def get_model(model: str) -> type[BaseModel]:
    """
    Models are used to encapsulate groups of parameters. They can
    be referenced in a analysis specification with "models.xxx.yyy."

    When building an actual analysis from a config file, this function
    will be called to return the actual class. The parameter object can
    then be constructed by passing the variables from the configuration
    file into the constructor of this class. The class will then
    provide any parsing and validation required.
    """
    path = model.split(".")
    if path[0] == "extern":
        return get_external_model(path[1:])
    elif path[0] != "models":
        raise AttributeError(
            f"Expected model path to start with 'models' but got {path[0]}"
        )
    obj = models
    for subpath in path[1:]:
        obj = getattr(obj, subpath)
    return obj


def get_external_model(model: List[str]) -> type[BaseModel]:
    """
    Cosmap allows users to design their own models for their own analyses.
    This function is used to find any models that have been installed, and
    grab them when needed. These model paths should be prefaced with
    "extern," so something like "extern.models.xxx.yyy"
    """
    raise NotImplementedError("External models are not yet supported")


def verify_model_params(model: type[BaseModel], params):
    return model(**params)


def find_common_params(base: TypeVar, model_to_check: BaseModel, skip=[]):
    """
    Finds any parameters in base (by name) that are also in model_to_check and
    returns them as key-value pairs. This is most often used when you have an
    analysis that creates other analyses, and some of the parameters for the
    sub-analyses are included in the parameters of the super-analysis. This
    automatically excludes any fields that are found in the base paramter specification.

    """
    standard_fields = set(AnalysisParameters.__fields__.keys())
    to_skip = set(skip)
    base_keys = set(base.__fields__.keys())

    keys_to_check_for = base_keys - to_skip - standard_fields
    output = {}
    for key in keys_to_check_for:
        if key in model_to_check.__fields__:
            value = getattr(model_to_check, key)
            if value is not None:
                output.update({key: value})

    return output
