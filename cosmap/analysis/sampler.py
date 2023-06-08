from abc import ABC, abstractmethod
from heinlein import Region


class Sampler(ABC):
    """
    A sampler selects subregions from a map for analysis.
    All samplers should inherit from this class.
    """
    def __init__(self, parameters):
        self.parameters = parameters

    @abstractmethod
    def generate_samples(self):
        pass

class RandomSampler(Sampler):
    pass

    def generate_samples(self):
        pass


class GridSampler(Sampler):
    pass

    def generate_samples(self):
        pass