from pydantic import BaseModel, Field, validator
from typing import List
from astropy.coordinates import SkyCoord
import astropy.units as u


class AstropyUnitfulParamter(BaseModel):
    """
    This Single Value Model consumes a value (or values)
    and a unit, and produces the associated astropy quantity or
    list of quantities. For example, the in a parameter block
    it could looks something like this::

        class MyModel(BaseModel):
            my_parameter: AstropyUnitfulParamter
            other_parameter: int
            yet_another parameter: float
    
    And then, in the associated json file, it could look like this::

        {
            my_parameter: {
                value: 10,
                units: "degree"
            }
            other_parameter: 10,
            yet_another_parameter: 3.5

        }
    """
    class Config:
        arbitrary_types_allowed = True

    units: u.Unit
    value: u.Quantity | List[u.Quantity]

    @validator("units", pre=True)
    def parse_units(cls, v):
        try:
            return getattr(u, v)
        except AttributeError:
            return v
    
    @validator("value", pre=True)
    def parse_value(cls, v, values):
        if type(v) != u.Quantity:
            if type(v) == list:
                a= [v*values["units"] for v in v]
                return a
            return v*values["units"]
        return v

    def get_value_type(self):
        return u.Quantity | List[u.Quantity]

    def get_value(self):
        return self.value
    


class SkyCoordinate(BaseModel):

    """
    The SkyCoordinate model consumes a list of two values and(optionally) a
    unit. It produces an astropy SkyCoord object. For example, in a parameter
    block it could look something like this::

        class MyModel(BaseModel):
            location: SkyCoordinate
            other_parameter: int
            yet_another parameter: float
    
    And then, in the associated json file, it could look like this::
        {
            location: {
                coordinate: [10, 20],
                units: ["deg", "deg"]
            },
            other_parameter: 5
            yet_another_parameter: 3.5
        }
    
    """
    units: List[str] = Field(
        ["deg", "deg"],
        min_items=1,
        max_items=2
    )
    class Config:
        arbitrary_types_allowed = True


    @validator("units", pre=True)
    def handle_units(cls, v):
        val = v if type(v) == list else [v]
        if len(val) == 1:
            type_ = val[0]
            output = [type_, type_]
        elif len(val) == 2:
            output = val
        else:
            raise ValueError("Skycoord's 'units' field should have one or two items")
        return output
    
    
    coordinate: SkyCoord

    @validator("coordinate", pre=True)
    def build_coordnate(cls, v, values):
        try:
            vals = list(v)
            if len(vals) != 2:
                raise TypeError
        except TypeError:
            raise TypeError("Skycoords 'coordinate' field should have two items")
        sk= SkyCoord(*vals, unit=values["units"])
        return sk
    
    def get_value_type(self):
        return SkyCoord
    def get_value(self):
        return self.coordinate
