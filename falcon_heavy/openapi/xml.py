from ..schema import types

from .extensions import SpecificationExtensions


Xml = types.Schema(
    name='Xml',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'name': types.StringType(),
        'namespace': types.StringType(),
        'prefix': types.StringType(),
        'attribute': types.BooleanType(),
        'wrapped': types.BooleanType()
    }
)
