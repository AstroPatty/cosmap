from pydantic import BaseModel, validator
import astropy.units as u
from astropy.coordinates import SkyCoord
from typing import List

class Circle(BaseModel):
    """
    Defines the expected values of a circle
    
    """
    units: u.Unit = u.arcmin
    radius: u.Quantity
    center: SkyCoord
    class Config:
        arbitrary_types_allowed = True
    
    @validator('units', pre=True)
    def handle_unit(cls, v):
        if type(v) == str:
            return getattr(u, v)
        return v

    @validator('radius', pre=True)
    def handle_units(cls, v, values):
        if not isinstance(v, u.Quantity):
            try:
                v = float(v)
            except ValueError:
                raise ValueError(f"Expected a number for the radius, got {v}")
            return v*values["units"]
        return v

    @validator('center', pre=True)
    def handle_center(cls, v):
        if type(v) == SkyCoord:
            return v
        return SkyCoord(*v, unit="deg")

