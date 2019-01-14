from ..schema import types

from .extensions import SpecificationExtensions


Example = types.Schema(
    name='Example',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'summary': types.StringType(),
        'description': types.StringType(),
        'value': types.AnyType(),
        'externalValue': types.StringType()
    }
)
