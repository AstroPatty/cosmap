from cosmap.plugins import register_plugins, register_specs

from . import plugins, task
from .errors import CosmapBadSampleError

__all__ = ["CosmapBadSampleError"]

register_specs(plugins)
register_plugins(task)
