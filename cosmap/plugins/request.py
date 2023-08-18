from .manager import manager

class CosmapPluginError(Exception):
    pass

def request(plugin_name: str):
    try:
        f = getattr(manager.hook, plugin_name)
    except AttributeError:
        raise CosmapPluginError(f"Unable to find plugin '{plugin_name}'!")
    return f