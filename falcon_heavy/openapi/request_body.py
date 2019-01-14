from ..schema import types

from .media_type import MediaType, content_type_validator
from .extensions import SpecificationExtensions


RequestBody = types.Schema(
    name='RequestBody',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'description': types.StringType(),
        'content': types.DictType(types.ObjectType(MediaType), required=True, validators=[content_type_validator]),
        'required': types.BooleanType(default=False)
    }
)
