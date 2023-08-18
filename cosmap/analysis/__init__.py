from .errors import CosmapBadSampleError
from . import plugins, task, sampler

from cosmap.plugins.manager import manager



__all__ = ['CosmapBadSampleError']

manager.add_hookspecs(plugins)


manager.register(task)
