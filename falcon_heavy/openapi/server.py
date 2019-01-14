from ..schema import types

from .extensions import SpecificationExtensions


ServerVariable = types.Schema(
    name='ServerVariable',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'enum': types.ArrayType(types.StringType()),
        'default': types.StringType(required=True),
        'description': types.StringType()
    }
)


Server = types.Schema(
    name='Server',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'url': types.StringType(required=True),
        'description': types.StringType(),
        'variables': types.DictType(types.ObjectType(ServerVariable))
    }
)
