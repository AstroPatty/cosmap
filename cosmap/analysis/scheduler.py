from typing import Protocol, runtime_checkable
from pydantic import BaseModel
from abc import ABC, abstractmethod
from cosmap.analysis.dependencies import build_dependency_graphs
from dask.distributed import Client, get_client
import networkx as nx
from loguru import logger
import os

class CosmapAnalysisExcept(Exception):
    pass

def load_transformations(analysis_parameters: BaseModel):
    output = {}
    for name, block in analysis_parameters.transformations.items():
        if not name[0].isupper():
            #This is not a block
            continue
        block_output = {}
        for transformation in block:
            block_definition = getattr(analysis_parameters.definition_module, name)
            block_output.update({transformation: getattr(block_definition, transformation)})
        output.update({name: block_output})
    return output


class Scheduler(ABC):
    """
    The scheduler handles interfacing with the library that manages resources
    on the machine. Currently, we only use dask, but in the future
    we could expand to use other schedulers.

    This base class defines the interface that all schedulers must implement, as well
    as some common functionality that all schedulers will need. The scheduler is responsible
    for keeping track of outputs, and making sure that the correct inputs are passed to each
    transformation. It is also responsible for making sure that the correct transformations are
    run in the correct order.
    """
    def initialize(self, parameters: BaseModel, client = None):
        self.parameters = parameters
        self.analysis_parameters = parameters.analysis_parameters
        self.dependency_graphs = build_dependency_graphs(self.analysis_parameters.transformations)
        self.transformation_objects = load_transformations(self.analysis_parameters)
        self.client = client
        self.futures = {}

    def schedule(self, blocks = []):
        """
        This method should define the main scheduling logic. A "block" is a set of transformations
        that work together in some way. For example, a block might be a set of transformations that
        are responsible for loading data from a file. Another block might be a set of transformations
        that are responsible for performing some computation on the data. 
        """
        raise NotImplementedError("This method must be implemented by the subclass")
    
    def get_task_parameters(self, block: str, task: str, previous_results = {}):
        """
        This method should return a dictionary of parameters that are needed to run the task. It will
        also search through previous results to see if any of them are required for the task. If so, it
        will add them to the dictionary of parameters. This method should be called by the subclass.
        """
        needed_parameters = self.analysis_parameters.transformations[block][task].get("needed-parameters", [])
        optional_parameters = self.analysis_parameters.transformations[block][task].get("optional-parameters", [])
        dependencies = self.analysis_parameters.transformations[block][task].get("dependencies", [])
        parameter_values = {}
        

        if type(dependencies) == list:
            parameter_values.update({p: previous_results[p] for p in dependencies})
        elif type(dependencies) == dict:
            for name, alias in dependencies.items():
                parameter_values.update({alias: previous_results[name]})
        
        
        if needed_parameters == "all":
            parameter_values.update({"parameters": self.analysis_parameters})
            return parameter_values
        
        all_parameters = needed_parameters + optional_parameters
        for param in all_parameters:
            param_path = param.split(".")
            if param_path[0] == "Main":
                obj = self.parameters
            else:
                obj = self.parameters.analysis_parameters
                param_path.insert(0, "analysis_parameters")
            for p in param_path[1:]:
                try:
                    obj = getattr(obj, p)

                except AttributeError:
                    if param in needed_parameters:
                        raise CosmapAnalysisExcept(f"Missing parameter {param}!")
                    else: #this is an optional parameter. I know that the "else" is not necessary but this is more readable, sue me
                        logger.info(f"No value found for optional parameter {param_path[-1]}... skipping")
                        obj = None
                        break


            parameter_values.update({param_path[-1]: obj})
        
        return parameter_values


class RandomSamplingScheduler(Scheduler):

    def schedule(self):
        pass

    def initialize(self, parameters: BaseModel):
        pass

class DefaultScheduler(Scheduler):
    """
    This scheduler is the default scheduler. It will schedule all blocks in the analysis using the most
    straightforward method possible. It will schedule each block in the order that they are defined in the
    analysis parameters. Individual transformations are responsible for asking the scheduler for the resources
    they need. 
    """
    def initialize(self, parameters: BaseModel, client = None):
        super().initialize(parameters, client)
        if not (saddress := os.environ.get("COSMAP_SCHEDULER_ADDRESS", False)):
            self.client = Client()
            address = self.client.cluster.scheduler_address
            os.environ.update({"COSMAP_SCHEDULER_ADDRESS":  address})
        else:
            self.client = get_client(saddress, timeout=2)
            self.client.upload_file(parameters.analysis_parameters.definition_module.__file__)

    def schedule(self, blocks = []):
        if self.client is None:
            self.client = Client(n_workers=self.parameters.threads)
        for block_name, block_values in self.transformation_objects.items():
            if not blocks or block_name in blocks:
                if block_name in self.futures:
                    raise CosmapAnalysisExcept(f"Block {block_name} already scheduled!")
                if not block_values:
                    continue
                block = self.schedule_block(block_name)

    def schedule_block(self, block_name: str, allow_user_input: bool = False):
        """
        Schedule a block of transformations. This method will schedule all transformations in the block.
        """

        self.futures[block_name] = {}

        if allow_user_input:
            tasks = []
        else:
            tasks = self.dependency_graphs[block_name]

        task_order = nx.topological_sort(tasks)
        for task in task_order:
            task_parameters = self.get_task_parameters(block_name, task, self.futures[block_name])
            task_object = self.transformation_objects[block_name][task]
            future = self.client.submit(task_object, **task_parameters)

            self.futures[block_name][task] = future

    def run_block(self, block_name):
        if block_name not in self.transformation_objects:
            raise CosmapAnalysisExcept(f"Block {block_name} not found!")
        elif block_name not in self.futures:
            raise CosmapAnalysisExcept(f"Block {block_name} not scheduled!")
        block = self.futures[block_name]
        output_transformations = [tname for tname in self.dependency_graphs[block_name].nodes if self.dependency_graphs[block_name].out_degree(tname) == 0]
        output = {}
        if output_transformations:
            for tname in output_transformations:
                if (output_name := self.analysis_parameters.transformations[block_name][tname].get("output-name")):
                    output.update({output_name: block[tname].result()})
                else:
                    output.update({tname: block[tname].result()})
        return output
    

class SingleThreadedScheduler(Scheduler):
    """
    This scheduler does not use a distributed computing framework. It's most often use for setup blocks that
    require user input.
    
    """
    def run_block(self, block_name):
        if block_name not in self.transformation_objects:
            raise CosmapAnalysisExcept(f"Block {block_name} not found!")
        
        tasks = self.dependency_graphs[block_name]
        task_order = nx.topological_sort(tasks)
        results = {}
        for task in task_order:
            task_parameters = self.get_task_parameters(block_name, task, results)
            task_object = self.transformation_objects[block_name][task]
            results[task] = task_object(**task_parameters)


        output_transformations = [tname for tname in self.dependency_graphs[block_name].nodes if self.dependency_graphs[block_name].out_degree(tname) == 0]
        output = {}
        if output_transformations:
            for tname in output_transformations:
                if (output_name := self.analysis_parameters.transformations[block_name][tname].get("output-name")):
                    output.update({output_name: results[tname]})
                else:
                    output.update({tname: results[tname]})
        return output
