from cosmap.analysis import utils

class CosmapPluginError(Exception):
    pass

allowed_types = ["worker-plugins"]

def verify_plugins(plugins, definitions):
    try:
        plugin_definitions = definitions.plugins
    except AttributeError:
        raise CosmapPluginError("Unable to find plugin definitions! Check that you have"\
                                " a 'plugins.py' file in your analysis directory.")
    missing = []
    for plugin_type, plugins_of_type in plugins.items():
        if plugin_type not in allowed_types:
            raise CosmapPluginError(f"Found unknown plugin type {plugin_type}!")
        for plugin_name in plugins_of_type:
            try:
                getattr(plugin_definitions, plugin_name)
            except AttributeError:
                raise CosmapPluginError(f"Unable to find definition of plugin '{plugin_name}' in plugins.py")

def initialize_plugins(analysis_object, plugins, parameters):
    if "worker-plugins" in plugins:
        initialize_worker_plugins(analysis_object, plugins["worker-plugins"], parameters)

def initialize_worker_plugins(analysis_object, plugins, parameters):
    for name, plugin_data in plugins.items():
        parameter_values = utils.get_parameters_by_name(parameters, parameter_names=plugin_data.get("needed-parameters", []))
        plugin_object = getattr(parameters.analysis_parameters.definition_module.plugins, name)(**parameter_values)
        analysis_object.client.register_worker_plugin(plugin_object)