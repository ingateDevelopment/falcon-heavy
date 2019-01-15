from __future__ import unicode_literals

import warnings

from wrapt import ObjectProxy

from mimeparse import best_match

from .._compat import Mapping

from ..schema import types
from ..schema.exceptions import SchemaError, Error

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .schema import SchemaObjectType
from .example import ExampleObjectType
from .enums import (
    PARAMETER_LOCATIONS,
    PARAMETER_STYLES
)


class ParameterContentMapType(types.AbstractType):

    MESSAGES = {
        'type': "Should be a mapping",
        'more_than_one_entry': "Should contains only one entry",
        'unsupported_media_content_type':
            "Unsupported media content type. Supported only the following content types: {0}"
    }

    __slots__ = [
        'subtype',
        'supported_content_types'
    ]

    def __init__(self, subtype, supported_content_types, **kwargs):
        super(ParameterContentMapType, self).__init__(**kwargs)
        self.subtype = subtype
        self.supported_content_types = supported_content_types

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping):
            raise SchemaError(Error(path, self.messages['type']))

        if len(raw) != 1:
            raise SchemaError(Error(path, self.messages['more_than_one_entry']))

        k, v = list(raw.items())[0]

        return k, self.subtype.convert(v, path / k, **context)

    def validate_content_type(self, converted, raw):
        content_type, _ = converted
        if not best_match(self.supported_content_types, content_type):
            return self.messages['unsupported_media_content_type'].format(
                ', '.join(sorted(self.supported_content_types)))


class ParameterObjectProxy(ObjectProxy):

    __slots__ = [
        '_self_path'
    ]

    def __init__(self, wrapped, path):
        super(ParameterObjectProxy, self).__init__(wrapped)
        self._self_path = path

    @property
    def path(self):
        return self._self_path

    @path.setter
    def path(self, value):
        self._self_path = value


class BaseParameterObjectType(BaseOpenApiObjectType):

    __slots__ = []

    MESSAGES = {
        'deprecated': "Parameter '{0}' is deprecated",
        'mutually_exclusive_schema_content_keywords': "The keywords `schema` and `content` are mutually exclusive"
    }

    PROPERTIES = {
        'description': types.StringType(),
        'required': types.BooleanType(default=False),
        'deprecated': types.BooleanType(default=False),
        'style': types.StringType(enum=PARAMETER_STYLES),
        'explode': types.BooleanType(),
        'allowReserved': types.BooleanType(
            enum=[False],
            messages={'enum': "`allowReserved` permanently unsupported"},
            default=False
        ),
        'schema': ReferencedType(SchemaObjectType()),
        'example': types.AnyType(),
        'examples': types.MapType(ReferencedType(ExampleObjectType())),
        'content': ParameterContentMapType(
            types.LazyType(lambda: MediaTypeObjectType()),
            ('application/json', )
        )
    }

    def _convert(self, raw, path, **context):
        converted = super(BaseParameterObjectType, self)._convert(raw, path, **context)

        if converted['deprecated']:
            warnings.warn(self.messages['deprecated'].format(path), DeprecationWarning)

        if 'explode' not in converted:
            converted.properties['explode'] = converted['style'] == PARAMETER_STYLES.FORM

        return ParameterObjectProxy(converted, path)

    def validate_mutually_exclusive_schema_content_keywords(self, converted, raw):
        if 'schema' in converted and 'content' in converted:
            return self.messages['mutually_exclusive_schema_content_keywords']


class NamedParameterObjectType(BaseParameterObjectType):

    PROPERTIES = {
        'name': types.StringType()
    }

    REQUIRED = {
        'name'
    }


class PathParameterObjectType(NamedParameterObjectType):

    __slots__ = []

    PROPERTIES = {
        'in': types.StringType(enum=(PARAMETER_LOCATIONS.PATH,)),
        'required': types.BooleanType(
            enum=[True],
            messages={'enum': "For path parameter this property must be True"}
        ),
        'style': types.StringType(
            enum=(
                PARAMETER_STYLES.SIMPLE,
                PARAMETER_STYLES.LABEL,
                PARAMETER_STYLES.MATRIX
            ),
            default=PARAMETER_STYLES.SIMPLE
        )
    }

    REQUIRED = {
        'in',
        'required'
    }


class QueryParameterObjectType(NamedParameterObjectType):

    __slots__ = []

    PROPERTIES = {
        'in': types.StringType(enum=(PARAMETER_LOCATIONS.QUERY,)),
        'allowEmptyValue': types.BooleanType(default=False),
        'style': types.StringType(
            enum=(
                PARAMETER_STYLES.FORM,
                PARAMETER_STYLES.SPACE_DELIMITED,
                PARAMETER_STYLES.PIPE_DELIMITED,
                PARAMETER_STYLES.DEEP_OBJECT
            ),
            default=PARAMETER_STYLES.FORM
        )
    }

    REQUIRED = {
        'in'
    }


class HeaderParameterObjectType(NamedParameterObjectType):

    __slots__ = []

    PROPERTIES = {
        'in': types.StringType(enum=(PARAMETER_LOCATIONS.HEADER,)),
        'style': types.StringType(enum=(PARAMETER_STYLES.SIMPLE, ), default=PARAMETER_STYLES.SIMPLE)
    }

    REQUIRED = {
        'in'
    }


class CookieParameterObjectType(NamedParameterObjectType):

    __slots__ = []

    PROPERTIES = {
        'in': types.StringType(enum=(PARAMETER_LOCATIONS.COOKIE,)),
        'style': types.StringType(enum=(PARAMETER_STYLES.FORM, ), default=PARAMETER_STYLES.FORM)
    }

    REQUIRED = {
        'in'
    }


ParameterPolymorphic = types.DiscriminatorType(
    property_name='in',
    mapping={
        PARAMETER_LOCATIONS.PATH: PathParameterObjectType(),
        PARAMETER_LOCATIONS.QUERY: QueryParameterObjectType(),
        PARAMETER_LOCATIONS.HEADER: HeaderParameterObjectType(),
        PARAMETER_LOCATIONS.COOKIE: CookieParameterObjectType()
    }
)


from .media_type import MediaTypeObjectType  # noqa
