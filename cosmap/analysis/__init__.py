from .errors import CosmapBadSampleError
from . import plugins, task

from cosmap.plugins.base import manager



__all__ = ['CosmapBadSampleError']

manager.add_hookspecs(plugins)
manager.register(task)
