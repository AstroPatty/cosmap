from pluggy import HookspecMarker, PluginManager

from .register import register

manager = PluginManager("cosmap")
pluginspsec = HookspecMarker("cosmap")


class CosmapPluginError(Exception):
    pass


def request(plugin_name: str):
    try:
        plugin = getattr(manager.hook, plugin_name)
    except AttributeError:
        raise CosmapPluginError(f"Unable to find plugin '{plugin_name}'!")

    if not plugin.get_hookimpls():
        raise CosmapPluginError(f"Plugin '{plugin_name}' has no hook implementations!")

    return plugin


__all__ = ["register", "request", "manager", "pluginspsec"]
