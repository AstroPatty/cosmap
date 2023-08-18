from abc import ABC, abstractmethod
from pydantic import BaseModel
import astropy.units as u
import builtins
import numpy as np
from astropy.coordinates import SkyCoord
from cosmap.plugins.base import manager, hookspec
from cosmap.plugins import register
from typing import final
from functools import partial

class CosmapSamplerException(Exception):
    pass

def Sampler(sampler_parameters: BaseModel, analysis_parameters: BaseModel, plugin = {}):
    if plugin:
        if len(plugin) > 1:
            raise CosmapSamplerException("Found multiple sampler plugins! Only one is allowed.")
        plugin_name, plugin_data = list(plugin.items())[0]
        plugin_object = plugin_data["plugin"]
        manager.register(plugin_object)
    else:
        sampler_type = sampler_parameters.sample_type
        match sampler_type:
            case "Random":
                manager.register(RandomSampler)
            case _:
                raise CosmapSamplerException(f"Could not find sampler type {sampler_type}")
    
    return CosmapSampler(sampler_parameters, analysis_parameters)

def get_frame_width(sample_shape: str, sample_dimensions):
    match sample_shape:
        case "Circle":
            try:
                return max(sample_dimensions)
            except AttributeError:
                return sample_dimensions
        case _:
            raise CosmapSamplerException(f"Could not find sample shape {sample_shape}")



class CosmapSamplerPlugins:

    @hookspec
    def initialize_sampler(sampler):
        pass

    @hookspec(firstresult=True)
    def generate_samples(sampler, n_samples):
        pass



@final
class CosmapSampler:
    """
    A sampler selects subregions from a map for analysis.
    Extensions to the cosmap sampler class are defined as 
    pluggy hooks. This sampler will check to make sure it has
    all the hooks necessary to run.
    """
    def __init__(self, sampler_parameters, analysis_parameters):
        self.sampler_parameters = sampler_parameters
        self.analysis_parameters = analysis_parameters
        self.manager = manager
        self.verify_plugins()
        self.build_frame()

    def verify_plugins(self):
        plugin_class = CosmapSamplerPlugins
        self.expected_impls = [k for k in dir(plugin_class) if not k.startswith("__")]
        missing = [c for c in self.expected_impls if not getattr(self.manager.hook, c).get_hookimpls()]
        if missing:
            raise CosmapSamplerException(f"Missing plugin implementations for {missing}")

    def __getattr__(self, name):
        """
        Automatically call the associated plugin IF it exists
        """

        if name in self.expected_impls:
            f = getattr(self.manager.hook, name)
            return partial(f, sampler=self)
        raise AttributeError(f"CosmapSampler object has no attribute \'{name}\'")

    def build_frame(self):
        """
        When sampling within a region, we actually have to sample within a slightly
        smaller region due to the size of the actual samples we are drawing. This
        region where we can't actually generate a sample in (but will overlap with the
        actual shape of the sample) is called the frame.
        """
        frame_size = get_frame_width(self.sampler_parameters.sample_shape, self.sampler_parameters.sample_dimensions)
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
        try:
            center = self.sampler_parameters.region_center
            dims = self.sampler_parameters.region_dimensions
            if dims is None:
                raise AttributeError
            full_bounds = [center.ra - dims[0]/2, center.dec - dims[1]/2, center.ra + dims[0]/2,  center.dec + dims[1]/2]
        except AttributeError:
            full_bounds = self.sampler_parameters.region_bounds

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
    



class RandomSampler:

    @register
    def generate_samples(sampler, n_samples):
        vals = sampler._sampler.uniform(sampler._low_sampler_range, sampler._high_sampler_range, size=(n_samples, 2))
        coords = sampler.samples_to_radec(vals[:,0], vals[:,1])
        coords = SkyCoord(coords[0], coords[1], unit="deg")
        return coords

    @register
    def initialize_sampler(sampler):
        sampler._sampler = np.random.default_rng()
    
