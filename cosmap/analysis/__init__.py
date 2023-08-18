from cosmap.plugins import manager

from . import plugins, task
from .errors import CosmapBadSampleError

__all__ = ["CosmapBadSampleError"]

manager.add_hookspecs(plugins)
manager.register(task)
