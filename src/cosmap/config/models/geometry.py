from typing import List

import astropy.units as u
from astropy.coordinates import SkyCoord
from pydantic import BaseModel, validator


class Circle(BaseModel):
    """
    Defines the expected values of a circle

    """

    units: u.Unit = u.arcmin
    radius: u.Quantity
    center: SkyCoord

    class Config:
        arbitrary_types_allowed = True

    @validator("units", pre=True)
    def handle_unit(cls, v):
        if isinstance(v, str):
            return getattr(u, v)
        return v

    @validator("radius", pre=True)
    def handle_units(cls, v, values):
        if not isinstance(v, u.Quantity):
            try:
                v = float(v)
            except ValueError:
                raise ValueError(f"Expected a number for the radius, got {v}")
            return v * values["units"]
        return v

    @validator("center", pre=True)
    def handle_center(cls, v):
        if type(v) == SkyCoord:
            return v
        return SkyCoord(*v, unit="deg")


class Rectangle(BaseModel):
    """ """

    bounds = List[u.Quantity]
    bound_units: u.Unit = u.degree

    class Config:
        arbitrary_types_allowed = True

    @validator("bounds", pre=True)
    def handle_bounds(cls, v, values):
        new_bounds = []
        for bound in v:
            if not isinstance(bound, u.Quantity):
                try:
                    bound = float(bound)
                except ValueError:
                    raise ValueError(f"Expected a number for the radius, got {bound}")
                new_bounds.append(bound * values["bound_units"])
        return bound * values["bound_units"]
