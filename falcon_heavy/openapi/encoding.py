from __future__ import unicode_literals

from six import string_types

from ..schema import types
from ..schema.exceptions import SchemaError, Error

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .media_type import CONTENT_TYPE_PATTERN
from .enums import PARAMETER_STYLES


class ContentTypesListType(types.AbstractType):

    MESSAGES = {
        'type': "Should be a string",
        'has_invalid_content_types': "The following content types are invalid: {0}"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if not isinstance(raw, string_types):
            raise SchemaError(Error(path, self.messages['type']))

        return [content_type.strip() for content_type in raw.split(',')]

    def validate_content_types(self, converted, raw):
        """Validates content types

        :param converted: list of content types
        :type converted: list
        :param raw: raw data
        :type raw: basestring
        """
        invalid_content_types = []
        for content_type in converted:
            if not CONTENT_TYPE_PATTERN.match(content_type):
                invalid_content_types.append(content_type)

        if invalid_content_types:
            return self.messages['has_invalid_content_types'].format(', '.join(sorted(invalid_content_types)))


class EncodingObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'contentType': ContentTypesListType(),
        'headers': types.MapType(ReferencedType(types.LazyType(lambda: HeaderObjectType()))),
        'style': types.StringType(
            enum=(
                PARAMETER_STYLES.FORM,
                PARAMETER_STYLES.SPACE_DELIMITED,
                PARAMETER_STYLES.PIPE_DELIMITED,
                PARAMETER_STYLES.DEEP_OBJECT
            ),
            default=PARAMETER_STYLES.FORM
        ),
        'explode': types.BooleanType(),
        'allowReserved': types.BooleanType(
            enum=[False],
            messages={'enum': "`allowReserved` permanently unsupported"},
            default=False
        )
    }

    def _convert(self, raw, path, **context):
        converted = super(EncodingObjectType, self)._convert(raw, path, **context)

        if 'explode' not in converted:
            converted.properties['explode'] = converted['style'] == PARAMETER_STYLES.FORM

        return converted


from .header import HeaderObjectType  # noqa
