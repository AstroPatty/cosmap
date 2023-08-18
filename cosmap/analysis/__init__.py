from .errors import CosmapBadSampleError
from . import plugins, task, sampler

from cosmap.plugins.base import manager



__all__ = ['CosmapBadSampleError']

manager.add_hookspecs(plugins)

manager.add_hookspecs(sampler.CosmapSamplerPlugins)


manager.register(task)
