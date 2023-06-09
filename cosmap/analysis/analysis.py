from __future__ import annotations
from typing import  Dict
from cosmap.analysis.transformation import Transformation
from cosmap.analysis.sampler import Sampler
from cosmap.analysis import scheduler, sampler
from cosmap.locations import ROOT
from networkx import DiGraph
from networkx.algorithms.dag import is_directed_acyclic_graph
import json
import uuid
from dask.distributed import Client, get_client
from loguru import logger
import sys
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
        self.setup()
 

    def setup(self, *args, **kwargs):

        self.sampler.initialize_sampler()
        self.sampler.generate_samples(10000)
        exit()
        blocks = []
        if "Setup" in self.parameters.analysis_parameters.transformations:
            single_scheduler = get_scheduler("SingleThreadedScheduler")
            single_scheduler.initialize(self.parameters)
            new_params = single_scheduler.run_block("Setup")
            self.parameters = self.update_parameters(self.parameters, {"analysis_parameters": new_params})
            self.scheduler.parameters = self.parameters
            self.scheduler.analysis_parameters = self.parameters.analysis_parameters
        new_blocks = [k for k in self.parameters.analysis_parameters.transformations.keys() if k not in self.ignore_blocks and k[0].isupper()]
        blocks.append(new_blocks)

        if blocks:
            self.scheduler.schedule(blocks)

    @staticmethod
    def update_parameters(old_paramters, new_params: dict):
        p_obj = old_paramters
        for name, values in new_params.items():
            param_path = name.split(".")
            for p in param_path[:-1]:
                p_obj = getattr(p_obj, p)

            if isinstance(getattr(p_obj, param_path[-1]), BaseModel):
                block = getattr(p_obj, name)
                updated_block = CosmapAnalysis.update_parameters(block, values)
                setattr(p_obj, name, updated_block)
        return old_paramters
            

    def run(self, *args, **kwargs):
        blocks = [k for k in self.parameters.analysis_parameters.transformations.keys() if k not in self.ignore_blocks and k[0].isupper()]
        results = {block: self.scheduler.run_block(block) for block in blocks}
        return results