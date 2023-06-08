from __future__ import annotations
from pydantic import BaseModel, Field
from pathlib import Path
from types import ModuleType
from dask.distributed import get_client
from cosmap.config.models import sky
import astropy.units as u
from astropy.coordinates import SkyCoord
from typing import Dict, Callable, List
"""
The parameter block is a top-level model that manages configuration
for a project, or some piece of the project. The parameter block
may contain exactly two things, a set of paramters and a set
of sub-blocks. Sub-block names are capitalized, while paramter
names are lower-case

A paramter block is built from two things: a template block,
which specifies which parameters and blocks are expected,
and an actual paramter specification, which contains values
for the associated paramters. Paramter specifications
should be understandable by PyDantic.

Parmaters with default values in the parameter specification
will be treated as optional.

Certain special types of paramters have been built into 
cosmap, which contain custom validators for things like astropy
units. To specify a paramter should use one of these pre-built models,
you can set the default paramter value in the specfications to 
"model.x.y" where x.y... is the models path. 



"""


class CosmapAnalysisParameters(BaseModel):
    definition_module: ModuleType = None
    definition_path: Path = None
    transformations: dict = {}
    class Config:
        arbitrary_types_allowed = True
class SamplingParameters(BaseModel):
    
    region_type: str = "Rectangle"
    region_center: sky.SkyCoordinate
    region_dimensions: sky.AstropyUnitfulParamter
    sample_type: str = "Circle"
    sample_dimensions: sky.AstropyUnitfulParamter
    class Config:
        arbitrary_types_allowed = True

class CosmapParameters(BaseModel):
    """
    The AnalysisParamters class is the base class for all analyis
    paramter objects. It keeps track of any paramters that are
    used inside the analysis itself. This base class defines
    a couple of fields that should be present for an analysis (even if
    they are not explicitly used). When designing an analysis, your
    configuration object should be a subclass of AnalysisParamters.
    
    Analysis paramters can be hierarchical: You can create a sub-block
    of parameters, if needed.

    """
    threads: int = Field(default = 1, ge=1)
    output_location = Path.cwd()
    analysis_parameters: CosmapAnalysisParameters = None
    sampling_parameters: SamplingParameters
    class Config:
        arbitrary_types_allowed = True

