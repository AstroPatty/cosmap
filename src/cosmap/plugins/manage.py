import json
from pathlib import Path

import loguru
from pluggy import HookimplMarker, HookspecMarker, PluginManager


class CosmapPluginException(Exception):
    pass


config = Path(__file__).resolve().parent / "plugins.json"
with open(config, "r") as f:
    plugin_config = json.load(f)

for name, pconfig in plugin_config.items():
    pconfig.update({"impl": False})

manager = PluginManager("cosmap")
pluginspec = HookspecMarker("cosmap")
register = HookimplMarker("cosmap")


def register_plugins(plugins: object):
    for name in dir(plugins):
        func = getattr(plugins, name)
        if hasattr(func, "cosmap_impl"):
            pconfig = plugin_config.get(name)
            if pconfig is None:
                raise CosmapPluginException(
                    f"Plugin `{name}` is not a valid cosmap plugin!"
                )
            elif pconfig["unique"] and pconfig["impl"]:
                loguru.logger.warning(
                    f"Plugin `{name}` is already registered!"
                    " The new plugin will overwrite the old one!"
                )

            pconfig["impl"] = True

    name = manager.register(plugins)


def register_specs(specifications: object):
    return manager.add_hookspecs(specifications)


def request(plugin_name: str):
    try:
        plugin = getattr(manager.hook, plugin_name)
    except AttributeError:
        raise CosmapPluginException(f"Unable to find plugin '{plugin_name}'!")

    if not plugin.get_hookimpls():
        raise CosmapPluginException(
            f"Plugin '{plugin_name}' has no hook implementations!"
        )
    return plugin
