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




def verify_plugins(plugins, definitions):
    try:
        plugin_definitions = definitions.plugins
    except AttributeError:
        raise CosmapPluginError("Unable to find plugin definitions! Check that you have"\
                                " a 'plugins.py' file in your analysis directory.")
    missing = []
    for plugin_name, plugin_data in plugins.items():
        if (pt:= plugin_data["plugin-type"]) not in allowed_types:
            raise CosmapPluginError(f"Found unknown plugin type {pt}!")

        try:
            getattr(plugin_definitions, plugin_name)
        except AttributeError:
            raise CosmapPluginError(f"Unable to find definition of plugin '{plugin_name}' in plugins.py")

def initialize_plugins(analysis_object, plugins, parameters):
    if hasattr (parameters.analysis_definition, "plugins"):
        manager.register(parameters.analysis_definition.plugins)
    
    output = {}
    for plugin, plugin_data in plugins.items():
        if (pt := plugin_data["plugin-type"]) == "sampler":
            _output = initialize_sampler_plugin(plugin, plugin_data, parameters)
            output.update({plugin_data["plugin-type"]: _output})
    return output

def initialize_worker_plugins(analysis_object, plugins, parameters):
    for name, plugin_data in plugins.items():
        parameter_values = utils.get_parameters_by_name(parameters, parameter_names=plugin_data.get("needed-parameters", []))
        plugin_object = getattr(parameters.analysis_definition.plugins, name)(**parameter_values)
        analysis_object.client.register_worker_plugin(plugin_object)

def initialize_sampler_plugin(name, plugin_data, parameters):
    parameter_values = utils.get_parameters_by_name(parameters, parameter_names=plugin_data.get("needed-parameters", []))
    plugin_object = getattr(parameters.analysis_definition.plugins, name)
    return {name: {"plugin": plugin_object, "parameters": parameter_values}}

def initialize_task_generator_plugin(name, plugin_data, parameters):
    parameter_values = utils.get_parameters_by_name(parameters, parameter_names=plugin_data.get("needed-parameters", []))
    plugin_object = getattr(parameters.analysis_definition.plugins, name)
    return {name: {"plugin": plugin_object, "parameters": parameter_values}}

