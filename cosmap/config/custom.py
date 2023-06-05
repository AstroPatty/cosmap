import param
from param.parameterized import instance_descriptor
import numbers
import astropy.units as u
from abc import ABC, abstractstaticmethod
from functools import singledispatchmethod
from typing import Any
from astropy.coordinates import SkyCoord
class ParamaterPlugin(ABC):
    pass

    @staticmethod 
    def parse_template(par, data, *args, **kwargs):
        pass
    
    @abstractstaticmethod 
    def parse_value(*args, **kwargs):
        pass

class AstropyUnits(ParamaterPlugin):
    def __init__(self, *args, **kwargs):
        pass
    
    def parse_template(self, par, data, *args, **kwargs):


        return astropyUnitfulParameter(par, data)

    def parse_value(self, val, units = None, *args, **kwargs):
        unit = getattr(u, units)
        try:
            new_list = [v*unit for v in val]
            return new_list
        except TypeError:
            return val*unit

class AstropyCoordinate(ParamaterPlugin):

    def parse_template(self, par, data, *args, **kwargs):
        return SkyCoordParam(par, data)

    def parse_value(self, val):
        print(val)
        print("1")

class listOrSingleParam(param.Parameter):
    __slots__ = ["allowed_type"]

    def __init__(self, base_param, *args, **params):
        super(listOrSingleParam, self).__init__(**params)
        self.allowed_type = base_param

    def __set__(self, attribute, value):
        if type(value) == list:
            try:
                new_vals = [self.allowed_type.check(v) for v in value]
                return super(listOrSingleParam, self).__set__(attribute, new_vals)
            except AttributeError:
                return super(listOrSingleParam, self).__set__(attribute, value)
        return super(listOrSingleParam, self).__set__(attribute, value)

    def _validate_value(self, value, allow_None):
        super()._validate_value(value, allow_None)
        if type(value) == list:
            try:
                for val in value:
                    self.allowed_type._validate_value(val, allow_None = False)
            except ValueError:
                raise ValueError(f"All values in this list must be of type {self.allowed_type}")
        
        else: 
            try:
                value = self.allowed_type._validate_value(value, allow_None = False)
            except ValueError:
                raise ValueError(f"Expected object of type {self.allowed_type} but got {type(value)}")

class astropyUnitfulParameter(param.Parameter):

    __slots__ = ["base_param", "allowed_units", "current_units"]

    def __init__(self, base_param, allowed_units, **params):
        super(astropyUnitfulParameter, self).__init__(**params)
        if type(allowed_units) != list:
            self.allowed_units = [allowed_units]
        else:
            self.allowed_units = allowed_units

        self.allowed_units = [getattr(u, v) for v in self.allowed_units]
        self.current_units = None
        self.base_param = base_param

    def __set__(self, obj: Any, val: list):
        if type(val) == list:
            print(val)
            if any([isinstance(v, u.Quantity) for v in val]):
                new_vals = val
            else:
                new_vals = [v*self.allowed_units[0] for v in val]
            super().__set__(obj, new_vals)
        elif type(val) != u.Quantity:
            super().__set__(obj, val*self.allowed_units[0])
        else:
            super().__set__(obj, val)
    def check(self, value):
        if not isinstance(value, u.Quantity):
            return value*self.allowed_units[0]
        return value

    def _validate_value(self, value, allow_None = False):
        super()._validate_value(value, allow_None)
        #note: override of __set__ ensures a unit will always be present
        try:
            if value.unit not in self.allowed_units:
                raise ValueError(f"Expected value with units {self._allowed_unit} but got {value.unit}")
        except AttributeError:
            value = value*self.allowed_units[0]

class SkyCoordParam(param.Parameter):

    __slots__ = ["radec"]
    def __init__(self, *args, **kwargs):
        super(SkyCoordParam, self).__init__(*args, **kwargs)
        self.radec = None
    def __set__(self, obj: Any, val: Any):
        self.radec = val
        try:
            coord = SkyCoord(*(val))
        except u.UnitTypeError:
            coord = SkyCoord(*val, unit="deg")
        super().__set__(obj, coord)
    
    def _validate_value(self, value, allow_None = False):
        if type(value) != SkyCoord:
            try:
                coord = SkyCoord(*(value))
            except u.UnitTypeError:
                coord = SkyCoord(*value, unit="deg")

triggers = {"units": astropyUnitfulParameter, "allow_multiple": listOrSingleParam}

def get_custom(param, pdata2):
    if not set(triggers.keys()).intersection(set(pdata2.keys())):
        return param 
    for tname, trigger in triggers.items():
        if tname not in pdata2.keys():
            continue
        param = trigger(param, pdata2[tname])
    return param

