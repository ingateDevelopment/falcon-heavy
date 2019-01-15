from __future__ import unicode_literals

import re

from six import iterkeys, iteritems

from ..schema import types

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .schema import SchemaObjectType
from .example import ExampleObjectType
from .enums import SCHEMA_TYPES


CONTENT_TYPE_PATTERN = re.compile(r'^((\w+/(\*|\w+))|(\*/\*)).*$', re.IGNORECASE)


class ContentMapType(types.MapType):

    __slots__ = []

    MESSAGES = {
        'has_invalid_content_types': "The following content types are invalid: {0}"
    }

    def validate_content_types(self, converted, raw):
        """Validates content types

        :param converted: dictionary with possible content definitions
        :type converted: Mapping
        :param raw: raw data
        :type raw: Mapping
        """
        invalid_content_types = []
        for content_type in iterkeys(converted):
            if not CONTENT_TYPE_PATTERN.match(content_type):
                invalid_content_types.append(content_type)

        if invalid_content_types:
            return self.messages['has_invalid_content_types'].format(', '.join(sorted(invalid_content_types)))


class MediaTypeObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'schema': ReferencedType(SchemaObjectType()),
        'example': types.AnyType(),
        'examples': types.MapType(ReferencedType(ExampleObjectType())),
        'encoding': types.MapType(types.LazyType(lambda: EncodingObjectType()))
    }

    def validate_encoding(self, converted, raw):
        encoding = converted.get('encoding')
        schema = converted.get('schema')

        if encoding is None or schema is None:
            return

        schema_type = schema.get('type')
        if schema_type != SCHEMA_TYPES.OBJECT:
            return

        schema_properties = schema.get('properties', {})

        not_defined_properties = []
        for property_name, property_encoding in iteritems(encoding):
            if property_name not in schema_properties:
                not_defined_properties.append(property_name)

        if not_defined_properties:
            return (
                "The key of `encoding`, being the property name, must exist in the `schema` as a property."
                " The following properties must be defined in `properties` of `schema`: {}".format(
                    ', '.join(sorted(not_defined_properties)))
            )


from .encoding import EncodingObjectType  # noqa
