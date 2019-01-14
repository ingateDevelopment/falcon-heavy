from ..schema import types

from .contact import Contact
from .license import License
from .extensions import SpecificationExtensions


Info = types.Schema(
    name='Info',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'title': types.StringType(required=True),
        'description': types.StringType(),
        'termsOfService': types.UrlType(),
        'contact': types.ObjectType(Contact),
        'license': types.ObjectType(License),
        'version': types.StringType(required=True)
    }
)
