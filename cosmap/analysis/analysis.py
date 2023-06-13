from __future__ import annotations
from typing import  Dict
from cosmap.analysis.transformation import Transformation
from cosmap.analysis.sampler import Sampler
from cosmap.dataset import get_dataset
from cosmap.analysis import scheduler, sampler
from cosmap.locations import ROOT
from cosmap.output import get_output_handler
from networkx import DiGraph
from networkx.algorithms.dag import is_directed_acyclic_graph
import json
import uuid
from dask.distributed import Client, get_client
from loguru import logger
from devtools import debug
from pydantic import BaseModel
from types import ModuleType
from typing import List
class AnalysisException(Exception):
    pass


def get_scheduler(scheduler_name: str):
    try:
        return getattr(scheduler, scheduler_name)()
    except AttributeError:
        raise AnalysisException(f"Could not find the scheduler {scheduler_name}")
    
class CosmapAnalysis:
    """
    The Analysis class is the central class of Cosmap. It defines
    a series of transformations which are applied in a particular sequence
    (or in parallel, where appropriate) to transform data from one form to
    another. 

    Cosmap is generally designed for analsyes that involve pulling data in some
    region from a dataset, performing some computation on that data, and then
    repeating many times.

    Distributed computing is handled by dask. Documentation to come...


    """
    ignore_blocks = ["Setup", "Teardown"]
    def __init__(self, analysis_paramters: BaseModel, **kwargs):
        self.parameters = analysis_paramters
        self.sampler = Sampler(self.parameters.sampling_parameters)
        self.dataset = get_dataset(self.parameters.dataset_parameters)
        self.setup()
 

    def setup(self, *args, **kwargs):

        self.sampler.initialize_sampler()
        self.sampler.generate_samples(10000)
        blocks = []
        if "Setup" in self.parameters.analysis_parameters.transformations:
            single_scheduler = get_scheduler("SingleThreadedScheduler")
            single_scheduler.initialize(self.parameters)
            new_params = single_scheduler.run_block("Setup")
            new_param_input = {}
            new_analysis_parameters = {}
            for name, block in new_params.items():
                if name.split(".")[0] == "Main":
                    new_param_input.update({".".join(name.split(".")[1:]): block})
                else:
                    new_analysis_parameters.update({name: block})
            if new_analysis_parameters:
                new_param_input.update({"analysis_parameters": new_analysis_parameters})
            
            self.parameters = self.update_parameters(self.parameters, new_param_input)


        self.output_handler = get_output_handler(self.parameters.output_parameters)
        exit()

        new_blocks = [k for k in self.parameters.analysis_parameters.transformations.keys() if k not in self.ignore_blocks and k[0].isupper()]
        blocks.append(new_blocks)

        if blocks:
            self.scheduler.schedule(blocks)

    @staticmethod
    def update_parameters(old_paramters, new_params: dict):
        for name, values in new_params.items():
            p_obj = old_paramters
            param_path = name.split(".")
            for p in param_path[:-1]:
                p_obj = getattr(p_obj, p)
            if not hasattr(p_obj, param_path[-1]):
                #We're attaching extra parameters. The block must
                #explicitly allow this, or Pydantic will throw an error
                setattr(p_obj, param_path[-1], values)
                continue

            if isinstance(getattr(p_obj, param_path[-1]), BaseModel):
                block = getattr(p_obj, name)
                updated_block = CosmapAnalysis.update_parameters(block, values)
                setattr(p_obj, name, updated_block)
            else:
                setattr(p_obj, param_path[-1], values)
        return old_paramters
    

    def run(self, *args, **kwargs):
        raise NotImplementedError