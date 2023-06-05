from __future__ import annotations
from typing import  Dict
from cosmap.analysis.transformation import Transformation
from cosmap.analysis import scheduler
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
    repeating many times. This core loop is itself defined as an analysis. This
    "top-level analysis" handles data management, while running a user-defined
    analysis.

    Distributed computing is handled by dask. Documentation to come...


    """
    ignore_blocks = ["Setup", "Teardown"]
    def __init__(self, analysis_paramters: BaseModel, **kwargs):
        self.parameters = analysis_paramters
        self.scheduler = get_scheduler(self.parameters.analysis_parameters.scheduler, **kwargs)
        self.scheduler.initialize(self.parameters)
        self.setup()    

    def setup(self, *args, **kwargs):
        if "Setup" in self.parameters.analysis_parameters.transformations:
            single_scheduler = get_scheduler("SingleThreadedScheduler")
            single_scheduler.initialize(self.parameters)
            new_params = single_scheduler.run_block("Setup")
            self.parameters = self.update_parameters(self.parameters, {"analysis_parameters": new_params})
            self.scheduler.parameters = self.parameters
            self.scheduler.analysis_parameters = self.parameters.analysis_parameters
        blocks = [k for k in self.parameters.analysis_parameters.transformations.keys() if k not in self.ignore_blocks and k[0].isupper()]
        if blocks:
            self.scheduler.schedule(blocks)

    @staticmethod
    def update_parameters(old_paramters, new_params: dict):
        for name, values in new_params.items():
            if isinstance(getattr(old_paramters, name), BaseModel):
                block = getattr(old_paramters, name)
                updated_block = CosmapAnalysis.update_parameters(block, values)
                setattr(old_paramters, name, updated_block)
            else:
                param_path = name.split(".")
                for p in param_path[:-1]:
                    old_paramters = getattr(old_paramters, p)
                setattr(old_paramters, param_path[-1], values)
        return old_paramters
            

    def run(self, *args, **kwargs):
        blocks = [k for k in self.parameters.analysis_parameters.transformations.keys() if k not in self.ignore_blocks and k[0].isupper()]
        results = {block: self.scheduler.run_block(block) for block in blocks}
        return results