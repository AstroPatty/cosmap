from pluggy import HookspecMarker, HookimplMarker, PluginManager


hookspec = HookspecMarker("cosmap")
register = HookimplMarker("cosmap")
manager = PluginManager("cosmap")

