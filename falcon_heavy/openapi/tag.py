from ..schema import types

from .external_documentation import ExternalDocumentation
from .extensions import SpecificationExtensions


Tag = types.Schema(
    name='Tag',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'name': types.StringType(required=True),
        'description': types.StringType(),
        'externalDocs': types.ObjectType(ExternalDocumentation)
    }
)
