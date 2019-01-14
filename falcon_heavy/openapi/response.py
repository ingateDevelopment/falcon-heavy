from ..schema import types

from .header import Header
from .media_type import MediaType, content_type_validator
from .link import Link
from .extensions import SpecificationExtensions


Response = types.Schema(
    name='Response',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'description': types.StringType(required=True),
        'headers': types.DictType(types.ObjectOrReferenceType(Header)),
        'content': types.DictType(types.ObjectType(MediaType), validators=[content_type_validator]),
        'links': types.DictType(types.ObjectOrReferenceType(Link))
    }
)
