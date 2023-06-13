from __future__ import annotations
from pydantic import BaseModel, Field, validator
from pathlib import Path
from types import ModuleType
from dask.distributed import get_client
from cosmap.config.models import sky
import astropy.units as u
from astropy.coordinates import SkyCoord
from typing import Dict, Callable, List
from pydantic import Extra
"""
The parameter block is a top-level model that manages configuration
for a project, or some piece of the project. The parameter block
may contain exactly two things, a set of paramters and a set
of sub-blocks.

A paramter block is built from two things: a template block,
which specifies which parameters and blocks are expected,
and a dictionary, which contains values
for the associated paramters. Paramter specifications
should be understandable by pydantic.

Parmaters with default values in the parameter specification
will be treated as optional.

Certain special types of paramters have been built into 
cosmap, which contain custom validators for things like astropy
units. To specify a paramter should use one of these pre-built models,
simply import the model. For example, to specify that a parameter
should be a sky coordinate, use::

    from cosmap.config.models import sky
    class MyParamters(BaseModel):
        my_param: sky.SkyCoordinate



"""

class CosmapAnalysisParameters(BaseModel):
    """
    Defines the parameters that will be used by the specific analysis.
    The definition_module and definition_path will be automatically filled in.
    This class should not be instatiated directly. Instead, use the 
    create_analysis_block function in cosmap.config.block.
    """
    definition_module: ModuleType = None
    transformations: dict = {}
    class Config:
        arbitrary_types_allowed = True
class CosmapSamplingParameters(BaseModel):
    """
    Cosmap analyses always involve repeating the same process on several
    different "regions" (samlles) of the sky. This class deifnes the parameters
    that are used to define the samples, and the greater region they are drawn from.
    The individual sampler will be responsible for actually evaluating the inputs here.
    """
    region_shape: str = "Rectangle"
    region_center: sky.SkyCoordinate = None
    region_dimensions: sky.AstropyUnitfulParamter = None
    region_bounds: sky.AstropyUnitfulParamter = None
    sample_shape: str = "Circle"
    sample_dimensions: sky.AstropyUnitfulParamter = None
    sample_type: str = "Random"
    class Config:
        arbitrary_types_allowed = True

    @validator("region_bounds")
    def validate_region_bounds(cls, v, values):
        if ("region_center" not in values or "region_dimensions" not in values) and v is None:
            raise ValueError("Either region_center and region_dimensions or region_bounds must be specified")

class CosmapDatasetParameters(BaseModel):
    """
    Cosmap analyses always involve repeatedly querying some large survey
    dataset. This block contains that information. The default wrapper is
    heinlein, which is optimized for large survey datasets.
    """
    dataset_name: str
    dataset_wrapper = "heinlein"

class CosmapOutputParameters(BaseModel):
    base_output_path = Path.cwd()
    output_paths: Path | dict = None
    output_formats: str | dict = "dataframe"
    write_format: str = "csv"
class CosmapParameters(BaseModel):
    """
    The CosmapParameters is the top-level parameter block
    that is used throughout the analysis. It contains
    a few parameters that are defined at a top-level (such as 
    the number of cores to use), but more importantly contains
    sub-blocks, which are used by various parts of the analysis.
    process.
    """
    threads: int = Field(default = 1, ge=1)
    output_parameters: CosmapOutputParameters
    analysis_parameters: CosmapAnalysisParameters = None
    sampling_parameters: CosmapSamplingParameters
    dataset_parameters: CosmapDatasetParameters
    class Config:
        arbitrary_types_allowed = True

