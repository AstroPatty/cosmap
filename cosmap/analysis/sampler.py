from abc import ABC, abstractmethod
from heinlein import Region
from pydantic import BaseModel
from devtools import debug

class CosmapSamplerException(Exception):
    pass

def Sampler(sampler_parameters: BaseModel):
    sampler_type = sampler_parameters.sample_type
    match sampler_type:
        case "Random":
            return RandomSampler(sampler_parameters)
        case "Grid":
            return GridSampler(sampler_parameters)
        case _:
            raise CosmapSamplerException(f"Could not find sampler type {sampler_type}")

class CosmapSampler(ABC):
    """
    A sampler selects subregions from a map for analysis.
    All samplers should inherit from this class.
    """
    def __init__(self, parameters):
        self.parameters = parameters

    @abstractmethod
    def generate_samples(self):
        pass

class RandomSampler(CosmapSampler):
    pass

    def generate_samples(self):
        pass


class GridSampler(CosmapSampler):
    pass

    def generate_samples(self):
        pass