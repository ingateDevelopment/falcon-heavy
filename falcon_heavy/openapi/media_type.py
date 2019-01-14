import re

from six import iterkeys

from ..schema import types, exceptions

from .schema import Schema
from .example import Example
from .extensions import SpecificationExtensions


CONTENT_TYPE_PATTERN = re.compile(r'^(\*|\w+)/(\*|\w+).*$', re.IGNORECASE)


def content_type_validator(value):
    """
    Validates content type. Content type can be specified like:
        application/json - accepts json content with anything parameters (such as application/json; charset=utf-8),
        application/json; charset=utf-8 - accept only utf-8 encoded content,
        application/* - accept all application content,
        */* - accept everything content.

    :param value: Dictionary with possible contents definition.
    :type value: dict
    """
    for content_type in iterkeys(value):
        if not CONTENT_TYPE_PATTERN.match(content_type):
            raise exceptions.ValidationError("Content type `{}` is invalid".format(content_type))


MediaType = types.Schema(
    name='MediaType',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'schema': types.ObjectOrReferenceType(Schema),
        'example': types.AnyType(),
        'examples': types.DictType(types.ObjectOrReferenceType(Example)),
        'encoding': types.DictType(types.ObjectType(lambda: Encoding))
    }
)


from .encoding import Encoding  # noqa
