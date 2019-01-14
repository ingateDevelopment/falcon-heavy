from ..schema import types

from .server import Server
from .extensions import SpecificationExtensions


Link = types.Schema(
    name='Link',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'operationRef': types.StringType(),
        'operationId': types.StringType(),
        'parameters': types.DictType(types.AnyType()),
        'requestBody': types.AnyType(),
        'description': types.StringType(),
        'server': types.ObjectType(Server)
    }
)
