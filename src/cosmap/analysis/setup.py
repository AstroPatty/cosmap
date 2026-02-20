import networkx as nx
from loguru import logger
from pydantic import BaseModel

from cosmap.analysis import dependencies, utils


class CosmapAnalysisExcept(Exception):
    pass


def handle_setup(parameters: BaseModel, transformations: dict):
    """
    This function is responsible for running the setup blocks. It will run the setup
    blocks in the order specified in the analysis parameters. It will also check to
    make sure that all of the required parameters are present.
    """
    dependency_graph = dependencies.build_dependency_graph(transformations["Setup"])
    task_order = nx.topological_sort(dependency_graph)
    transformation_objects = utils.load_transformations(parameters, block_="Setup")
    return run_setup(parameters, dependency_graph, transformation_objects, task_order)


def run_setup(parameters, dependency_graph, transformation_objects, task_order):
    analysis_parameters = parameters.analysis_parameters
    results = {}
    block_name = "Setup"
    for task in task_order:
        task_parameters = get_task_parameters(parameters, task, results)
        task_object = transformation_objects[block_name][task]
        results[task] = task_object(**task_parameters)

    output_transformations = [
        tname
        for tname in dependency_graph.nodes
        if dependency_graph.out_degree(tname) == 0
    ]
    output_transformations.extend(
        [
            tname
            for tname in dependency_graph.nodes
            if analysis_parameters.transformations[block_name][tname].get("output")
        ]
    )
    output_transformations = set(output_transformations)
    output = {}
    if output_transformations:
        for tname in output_transformations:
            if output_name := analysis_parameters.transformations[block_name][
                tname
            ].get("output-name"):
                output.update({output_name: results[tname]})
            else:
                output.update({tname: results[tname]})
    return output


def get_task_parameters(parameters: BaseModel, task: str, previous_results={}):
    """
    This method should return a dictionary of parameters that are needed to run the
    task. It will also search through previous results to see if any of them are
    required for the task. If so, it will add them to the dictionary of parameters.
    This method should be called by the subclass.
    """
    block = "Setup"
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
                obj = getattr(obj, p)

            except AttributeError:
                if param in needed_parameters:
                    raise CosmapAnalysisExcept(f"Missing parameter {param}!")
                else:  # this is an optional parameter. I know that the "else" is not
                    # necessary but this is more readable, sue me
                    logger.info(
                        f"No value found for optional parameter {param_path[-1]}..."
                    )
                    obj = None
                    break

        if type(obj) == BaseModel:
            obj = obj.dict()
        parameter_values.update({param_path[-1]: obj})

    return parameter_values
