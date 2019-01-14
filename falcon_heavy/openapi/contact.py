from ..schema import types

from .extensions import SpecificationExtensions


Contact = types.Schema(
    name='Contact',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'name': types.StringType(),
        'url': types.UrlType(),
        'email': types.EmailType()
    }
)
