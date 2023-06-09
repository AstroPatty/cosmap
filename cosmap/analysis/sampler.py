from abc import ABC, abstractmethod
from heinlein import Region
from pydantic import BaseModel
from devtools import debug
from heinlein import Region
import astropy.units as u
import builtins
import numpy as np
import matplotlib.pyplot as plt
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

def get_frame_width(sample_shape: str, sample_dimensions):
    match sample_shape:
        case "Circle":
            try:
                return max(sample_dimensions)
            except AttributeError:
                return sample_dimensions
        case _:
            raise CosmapSamplerException(f"Could not find sample shape {sample_shape}")

class CosmapSampler(ABC):
    """
    A sampler selects subregions from a map for analysis.
    All samplers should inherit from this class.
    """
    def __init__(self, parameters):
        self.parameters = parameters
        self.build_frame()

    def build_frame(self):
        """
        When sampling within a region, we actually have to sample within a slightly
        smaller region due to the size of the actual samples we are drawing. This
        region where we can't actually generate a sample in (but will overlap with the
        actual shape of the sample) is called the frame.
        """
        frame_size = get_frame_width(self.parameters.sample_shape, self.parameters.sample_dimensions)
        match type(frame_size):
            case u.Quantity:
                frame_width = frame_size
                frame_height = frame_size
            case builtins.list:
                frame_width = frame_size[0]
                frame_height = frame_size[1]
            case _:
                raise CosmapSamplerException(f"Could not find frame size {frame_size}")

        df = [-frame_width, -frame_height, frame_width, frame_height]
        center = self.parameters.region_center
        dims = self.parameters.region_dimensions
        full_bounds = [center.ra - dims[0]/2, center.dec - dims[1]/2, center.ra + dims[0]/2,  center.dec + dims[1]/2]
        self.frame = [full_bounds[i] + df[i] for i in range(4)]
        self.initialize_sampler_bounds()

    def initialize_sampler_bounds(self):
        """
        Since we're working on the surface of a sphere, we have to do a bit
        of extra work to make sure our samples are spaced evenly in the region.
        """
        ra1,dec1,ra2,dec2 = *[v.to(u.radian).value for v in self.frame],
        ra_range = (min(ra1, ra2), max(ra1, ra2))
        dec_range = (min(dec1, dec2), max(dec1, dec2))
        #Keeping everything in radians for simplicity
        #Convert from declination to standard spherical coordinates
        phi_range = ra_range
        theta_range = (np.pi / 2. - dec_range[0], np.pi / 2. - dec_range[1])
        #Area element on a sphere is dA = d(theta)d(cos[theta])
        #Sampling uniformly on the surface of a sphere means sampling uniformly
        #Over cos theta
        costheta_range = np.cos(theta_range)
        self._low_sampler_range = [phi_range[0], costheta_range[0]]
        self._high_sampler_range = [phi_range[1], costheta_range[1]]
    
    @staticmethod
    def samples_to_radec(phis, thetas):
        """
        Convert values drawn from the sample to ra, dec coordinates
        """
        ras = np.degrees(phis)*u.degree
        decs = (90 - np.degrees(np.arccos(thetas)))*u.degree
        return np.array([ras, decs])
    
    @abstractmethod
    def initialize_sampler(self):
        pass

    @abstractmethod
    def generate_samples(self):
        pass


class RandomSampler(CosmapSampler):

    def generate_samples(self, n_samples):
        vals = self._sampler.uniform(self._low_sampler_range, self._high_sampler_range, size=(n_samples, 2))
        coords = self.samples_to_radec(vals[:,0], vals[:,1])
        return coords

    def initialize_sampler(self):
        self._sampler = np.random.default_rng()
    

class GridSampler(CosmapSampler):

    def initialize_sampler(self):
        """
        No work required
        """
        return

    def generate_samples(self, n_samples):
        """
        Generate n_samples on the surface of the sphere that are
        evenly spaced. 
        """
        pass