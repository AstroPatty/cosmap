from cosmap.analysis import utils
from cosmap.analysis.sampler import CosmapSampler
from cosmap.plugins.manager import pluginspsec
from cosmap.plugins.manager import manager
from pydantic import BaseModel
import networkx as nx


class CosmapPluginError(Exception):
    pass

allowed_types = ["sampler", "task_generator"]


@pluginspsec(firstresult=True)
def generate_tasks(client, parameters: BaseModel, dependency_graph: nx.DiGraph, needed_dtypes: list, samples: list, chunk_size: int = 1000):
    """
    Generates tasks for the scheduler to execute. This function is called by the scheduler. This is an advanced function, and you should
    only overwrite if you really know what you're doing and have a very good reason that the default task generation won't work for you.
    """
    pass

@pluginspsec
def initialize_sampler(sampler: CosmapSampler, sampling_parameters: BaseModel, analysis_parameters: BaseModel):
    """
    Do any initialization necessary. Any state updates should be made to the sampler object itself.
    This function will also recieve the sampling parameters and analysis parameters from the full
    parameter block.
    """
    pass

@pluginspsec(firstresult=True)
def generate_samples(sampler, n_samples):
    """
    Generate samples from the sampler. This function should return a list of samples.
    """
    pass




