from loguru import logger
from pydantic import BaseModel

from cosmap.analysis.analysis import CosmapAnalysis
from cosmap.config.block import create_analysis_block


class CosmapConfigException(Exception):
    pass


def build_analysis_object(analysis_data, run_configuration, **kwargs):
    """
    Construct an analysis object, assuming the analysis has been installed
    by `cosmap install`

    Parameters
    ----------
    base_analysis: str
        The name of the analysis
    config: dict
        The configuration for the analysis, usually read from a file

    Returns
    -------
    analysis_object: CosmapAnalysis
    """
    module = analysis_data["module"]
    transformations = analysis_data["transformations"]
    additional_parameters = analysis_data["parameters"]
    plugins = analysis_data.get("plugins", {})
    run_configuration.update(
        {"analysis_definition": module, "transformations": transformations}
    )
    if plugins:
        run_configuration.update({"plugins": plugins})
    config_definition = getattr(module, "config")
    try:
        main_config_definition = getattr(config_definition, "Main")
    except AttributeError:
        raise CosmapConfigException(
            f"The analysis config for '{module.__name__}'"
            "does not have a 'Main' config block"
        )

    run_configuration = update_nested_dict(run_configuration, additional_parameters)
    block = create_analysis_block("Main", main_config_definition, run_configuration)
    block.analysis_parameters.transformations = transformations
    analysis_object = CosmapAnalysis(
        analysis_paramters=block, plugins=plugins, **kwargs
    )
    return analysis_object


def update_nested_dict(original, update):
    for key, value in update.items():
        if key not in original:
            original[key] = value

        elif isinstance(value, dict):
            original[key] = update_nested_dict(original[key], value)
        else:
            original[key] = value

    return original


def load_transformations(parameters: BaseModel, block_=None):
    output = {}
    definition_module = getattr(parameters.analysis_definition, "transformations")
    for name, block in parameters.analysis_parameters.transformations.items():
        if block is not None and name != block_:
            continue
        block_output = {}
        try:
            block_definition = getattr(definition_module, name)
        except AttributeError:
            raise CosmapConfigException(
                f"Could not find the definitions for block {name}!"
            )

        for transformation in block:
            block_output.update(
                {transformation: getattr(block_definition, transformation)}
            )
        output.update({name: block_output})
    return output


def get_parameters_by_name(parameters: BaseModel, parameter_names: list):
    parameter_values = {}
    for param in parameter_names:
        param_path = param.split(".")
        if param_path[0] == "Main":
            obj = parameters
        else:
            obj = parameters.analysis_parameters
            param_path.insert(0, "analysis_parameters")
        for p in param_path[1:]:
            try:
                obj = getattr(obj, p)

            except AttributeError:
                print(p)
                if param in parameter_names:
                    raise CosmapConfigException(f"Missing parameter {param}!")
                else:  # this is an optional parameter. I know that the "else" is not
                    # necessary but this is more readable, sue me
                    logger.info(
                        f"No value found for optional parameter {param_path[-1]}..."
                    )
                    obj = None
                    break

        parameter_values.update({param_path[-1]: obj})

    return parameter_values


def get_task_parameters(
    parameters: BaseModel, block: str, task: str, previous_results={}
):
    """
    This method should return a dictionary of parameters that are needed to run the
    task. It will also search through previous results to see if any of them are
    required for the task. If so, it will add them to the dictionary of parameters.
    This method should be called by the subclass.
    """
    analysis_parameters = parameters.analysis_parameters
    needed_parameters = analysis_parameters.transformations[block][task].get(
        "needed-parameters", []
    )
    optional_parameters = analysis_parameters.transformations[block][task].get(
        "optional-parameters", []
    )
    dependencies = analysis_parameters.transformations[block][task].get(
        "dependencies", []
    )
    parameter_values = {}
    if previous_results:
        if isinstance(dependencies, list):
            parameter_values.update({p: previous_results[p] for p in dependencies})
        elif isinstance(dependencies, dict):
            for name, alias in dependencies.items():
                parameter_values.update({alias: previous_results[name]})

    all_parameters = needed_parameters + optional_parameters
    for param in all_parameters:
        param_path = param.split(".")
        if param_path[0] == "Main":
            obj = parameters
        else:
            obj = analysis_parameters
            param_path.insert(0, "analysis_parameters")
        for p in param_path[1:]:
            try:
                obj = getattr(obj, p)

            except AttributeError:
                if param in needed_parameters:
                    raise CosmapConfigException(f"Missing parameter {param}!")
                else:
                    logger.info(
                        f"No value found for optional parameter {param_path[-1]}..."
                    )
                    obj = None
                    break

        parameter_values.update({param_path[-1]: obj})

    return parameter_values


def get_task_parameters_from_dictionary(
    parameters: BaseModel, block: str, task: str, previous_results={}
):
    """
    This method should return a dictionary of parameters that are needed to run the
    task. It will also search through previous results to see if any of them are
    required for the task. If so, it will add them to the dictionary of parameters.
    This method should be called by the subclass.
    """
    analysis_parameters = parameters["analysis_parameters"]
    needed_parameters = analysis_parameters["transformations"][block][task].get(
        "needed-parameters", []
    )
    optional_parameters = analysis_parameters["transformations"][block][task].get(
        "optional-parameters", []
    )
    dependencies = analysis_parameters["transformations"][block][task].get(
        "dependencies", []
    )
    parameter_values = {}

    if isinstance(dependencies, list):
        parameter_values.update({p: previous_results[p] for p in dependencies})
    elif isinstance(dependencies, dict):
        for name, alias in dependencies.items():
            parameter_values.update({alias: previous_results[name]})

    if needed_parameters == "all":
        parameter_values.update({"parameters": analysis_parameters})
        return parameter_values

    all_parameters = needed_parameters + optional_parameters
    for param in all_parameters:
        param_path = param.split(".")
        if param_path[0] == "Main":
            obj = parameters
        else:
            obj = analysis_parameters
            param_path.insert(0, "analysis_parameters")
        for p in param_path[1:]:
            try:
                obj = obj[p]

            except KeyError:
                if param in needed_parameters:
                    raise CosmapConfigException(f"Missing parameter {param}!")
                else:
                    logger.info(
                        f"No value found for optional parameter {param_path[-1]}..."
                    )
                    obj = None
                    break

        parameter_values.update({param_path[-1]: obj})

    return parameter_values
