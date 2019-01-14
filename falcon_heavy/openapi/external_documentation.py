from ..schema import types

from .extensions import SpecificationExtensions


ExternalDocumentation = types.Schema(
    name='ExternalDocumentation',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'description': types.StringType(),
        'url': types.UrlType(required=True)
    }
)
