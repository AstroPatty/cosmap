from typing import Protocol, Type, TypeVar, runtime_checkable

from . import sky

__all__ = ["sky", "SingleValueModel"]


T = TypeVar("T")
"""
A 'model' is used in the context of this library in a very similar
way to how it is used in Pydantic. It is a class containing a set
of parameters with specified types, that may or may not include
default values. The parameters are specified in a configuration
file, and then passed to the model, which will parse and validate
them. The model will then be used by an Analysis object to manage
its configuration.
"""


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

    This is just a protocol. Implementations should inherit from pydantic.BaseModel.
    Implementations may use all of pydantic's features to validate the parameter input,
    and may take in as many parameters as is necessary. However, they must define the
    get_value_type and get_value methods.

    When a SingleValueModel is included inside another model that is being parsed
    into a Parameter Block, the SingleValueModel will be replaced with the value
    returned by get_value. The value returned by get_value will be type-checked against
    the type returned by get_value_type.
    """

    def get_value_type(self) -> Type[T]:
        """
        Return the type of the value that this model will produce.
        It may be a union type. For, example:

        return u.Quantity | List[u.Quantity]

        is valid.
        """
        pass

    def get_value(self) -> T:
        """
        Return the value after all the information is parsed. This must be
        a "single value" in the sense that it must be representable as a
        single python object, not in the sense that it must be a scalar quantity.
        """
        pass
