from pydantic import BaseModel
from dask.distributed import get_worker
from dask import delayed
import astropy.units as u
import numpy as np
import math
from types import ModuleType
import networkx as nx
from cosmap.analysis import utils
from functools import partial
from devtools import debug
from cosmap import analysis
from loguru import logger

def generate_tasks(client, parameters: BaseModel, dependency_graph: nx.DiGraph, needed_dtypes: list, samples: list, chunk_size: int = 100):
    """
    

    chunk_size breaks up the computation such that results will be written to disk.
    
    
    """
    pipeline_function = build_pipeline(parameters, dependency_graph)
    n_chunks = math.ceil(len(samples) / chunk_size)
    n_workers = len(client.nthreads())
    chunks = np.array_split(samples, n_chunks)
    for c in chunks:
        splits = np.array_split(c, n_workers)
        f = partial(main_task, dtypes = needed_dtypes, pipeline_function = pipeline_function)
        tasks = client.map(f, splits)
        yield tasks


def build_pipeline(parameters, dependency_graph):
    """
    Build the pipeline that will actually run the analysis for a single
    iteration. In essence, we just chain all the invidual tasks together
    to form a pipeline.
    """
    transformations = parameters.analysis_parameters.transformations["Main"]
    transformation_defs = parameters.analysis_parameters.definition_module.transformations.Main
    task_order = list(nx.topological_sort(dependency_graph))
    if not transformations[task_order[-1]].get("is-output"):
        raise Exception("The last task in the pipeline must be an output task!")
    elif any([transformations[t].get("output") for t in task_order[:-1]]):
        raise Exception("Only the last task in the pipeline can be an output task!")
    #We can't pass pydantic objects, so we grab the parameters here
    param_dict = parameters.dict()
    param_dict["analysis_parameters"].pop("definition_module")
    pipeline_function = partial(
        pipeline,
        parameters = param_dict,
        transformations = transformations,
        transformation_definitions = transformation_defs,
        task_order = task_order
    )
    return pipeline_function    

def main_task(coordinates, dtypes, pipeline_function, *args, **kwargs):
    worker = get_worker()
    dataset = worker.dataset
    sample_generator = dataset.sample_generator(coordinates, dtypes = dtypes)
    results = []
    for sample in sample_generator:
        try:
            results.append(pipeline_function(data = sample))
        except analysis.CosmapBadSampleError:
            logger.warning("Bad sample detected. Skipping...")
            continue
    return results


def pipeline(data: dict, parameters: dict, transformations: dict, transformation_definitions: ModuleType, task_order: list):
    outputs = {}

    for task in task_order:
        needed_data = transformations[task].get("needed-data", [])
        inputs = {n: data[n] for n in needed_data}
        needed_parameters = utils.get_task_parameters_from_dictionary(parameters, "Main", task, outputs)
        inputs.update(needed_parameters)
        result = getattr(transformation_definitions, task)(**inputs)
        outputs.update({task: result})
    return outputs[task_order[-1]]