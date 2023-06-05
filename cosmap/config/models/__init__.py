from . import geometry, sky
from typing import Protocol, Type, runtime_checkable, TypeVar

__all__ = ["geometry", "sky", "SingleValueModel"]


T = TypeVar('T')

@runtime_checkable
class SingleValueModel(Protocol):
    """
    In astronomy, there are a decent amount of units and such that
    can be parsed into a single value. When specified in a configuration
    file though, numerical values and the associated units will need to be
    a seperate field. A SingleValueModel is a pydantic model that
    consumes multiple fields in a configuration file, but returns 
    a single value. It nees to define methods that specifies the type
    it will return, and actually returns the object.
    
    """

    def get_value_type(self) -> Type[T]:
        pass
    
    def get_value(self) -> T:
        pass