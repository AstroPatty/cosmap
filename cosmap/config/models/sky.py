from typing import Annotated, Any, Callable

import astropy.units as u
from astropy.coordinates import SkyCoord as SkC
from pydantic import BaseModel, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


def quantity_validator(v: dict, *args, **kwargs) -> u.Quantity:
    unit = getattr(u, v["units"])
    return u.Quantity(v["value"], unit=unit)


def quantity_serializer(quantity):
    return {"value": quantity.value, "unit": quantity.unit.to_string()}


quantity_dict_schema = core_schema.chain_schema(
    [
        core_schema.dict_schema(),
        core_schema.no_info_plain_validator_function(quantity_validator),
    ]
)


class _QuantityAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: Callable[[Any], core_schema.CoreSchema]
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=quantity_dict_schema,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(u.Quantity), quantity_dict_schema]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: x),
        )


Quantity = Annotated[u.Quantity, _QuantityAnnotation]


def sky_coord_validator(v: dict, *args, **kwargs) -> SkC:
    if type(v) == SkyCoord:
        return v
    else:
        return SkyCoord(*v["coordinate"], unit=v["units"])


def sky_coord_serializer(value):
    print(value)
    return {
        "coordinate": [value.ra.value, value.dec.value],
        "units": [value.ra.unit.to_string(), value.dec.unit.to_string()],
    }


sky_coord_dict_schema = core_schema.chain_schema(
    [
        core_schema.dict_schema(),
        core_schema.no_info_plain_validator_function(sky_coord_validator),
    ]
)


class _SkyCoordAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: Callable[[Any], core_schema.CoreSchema]
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=sky_coord_dict_schema,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(SkC), sky_coord_dict_schema]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: x),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(_core_schema.json_schema())


SkyCoord = Annotated[SkC, _SkyCoordAnnotation]

if __name__ == "__main__":

    class main(BaseModel):
        test: SkyCoord

    a = main(test=SkyCoord(1, 2, unit="deg"))
    print(a.model_dump())
