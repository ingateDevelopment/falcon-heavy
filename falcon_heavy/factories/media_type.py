from __future__ import unicode_literals

from six import iteritems

from mimeparse import best_match

from http.datastructures import FormStorage, FileStorage

from ..openapi.enums import (
    SCHEMA_TYPES,
    SCHEMA_FORMATS,
    PARAMETER_LOCATIONS,
    PARAMETER_STYLES
)

from ..schema import types
from ..schema.undefined import Undefined
from ..schema.exceptions import SchemaError, Error

from .media_deserializers import media_deserializers
from .parameters import ParametersType, ParameterType, ParameterFactory, IdentityParameterStyle
from .parameter_styles import PARAMETER_STYLE_CLASSES


class PartType(types.AbstractConvertible):

    MESSAGES = {
        'type': "Should be an instance of `FormStorage` or `FileStorage` classes",
        'not_allowed_content_type': "Not allowed content type '{0}'. Only the following content types are allowed: {1}",
        'invalid_media': "Invalid media"
    }

    __slots__ = [
        'subtype',
        'allowed_content_types',
        'headers_type'
    ]

    def __init__(self, subtype, allowed_content_types=None, headers_type=None, **kwargs):
        super(PartType, self).__init__(**kwargs)
        self.subtype = subtype
        if allowed_content_types is not None and not isinstance(allowed_content_types, (tuple, list)):
            allowed_content_types = (allowed_content_types, )
        self.allowed_content_types = allowed_content_types
        self.headers_type = headers_type

    def convert(self, raw, path, strict=True, **context):
        if raw is Undefined or raw is None:
            return self.subtype.convert(raw, path, strict=strict, **context)

        if not isinstance(raw, (FormStorage, FileStorage)):
            raise SchemaError(Error(path, self.messages['type']))

        content_type = raw.content_type

        if content_type and self.allowed_content_types:
            if not best_match(self.allowed_content_types, content_type):
                message = self.messages['not_allowed_content_type'].format(
                    content_type, ', '.join(sorted(self.allowed_content_types)))
                raise SchemaError(Error(
                    path / 'headers' / 'content-type',
                    message
                ))

        headers = raw.headers
        if headers and self.headers_type is not None:
            headers = self.headers_type.convert(headers, path / 'headers', **context)
            headers['content-type'] = content_type

        if isinstance(raw, FileStorage):
            value = raw.stream
        else:
            value = raw.value

            deserializer = media_deserializers.find_by_media_type(content_type)
            if deserializer is not None:
                value = deserializer(value)

        converted = self.subtype.convert(value, path, strict=False, **context)
        if isinstance(raw, FileStorage):
            return FileStorage(
                stream=converted,
                filename=raw.filename,
                content_length=raw.content_length,
                headers=headers
            )
        else:
            return FormStorage(
                value=converted,
                headers=headers
            )


class AbstractMediaTypeFactory(object):

    def __init__(self, property_factory):
        self.property_factory = property_factory

    def _generate(self, schema, encoding=None):
        raise NotImplementedError

    def generate(self, schema, encoding=None):
        schema_type = schema.get('type')

        if schema_type == SCHEMA_TYPES.OBJECT and not schema.subschemas:
            return self._generate(schema, encoding=encoding)

        return self.property_factory.generate(schema)


class MultipartMediaTypeFactory(AbstractMediaTypeFactory):

    def __init__(self, property_factory, headers_factory):
        super(MultipartMediaTypeFactory, self).__init__(property_factory)
        self.headers_factory = headers_factory

    @staticmethod
    def get_default_content_type(schema):
        """Returns default content type for part of multipart content by schema.

        :param schema: Schema object.
        :type schema: Object
        :return: Default content type.
        :rtype: basestring
        """
        schema_type = schema.get('type')
        schema_format = schema.get('format')

        if schema_type in (SCHEMA_TYPES.ARRAY, SCHEMA_TYPES.OBJECT):
            return 'application/json'

        elif schema_type == SCHEMA_TYPES.STRING and \
                schema_format in (SCHEMA_FORMATS.BINARY, SCHEMA_FORMATS.BYTE):
            return 'application/octet-stream'

        elif schema_type is not None:
            return 'text/plain'

        else:
            return

    def _generate_part(self, schema, property_encoding=None):
        allowed_content_types = None
        headers = None
        if property_encoding is not None:
            allowed_content_types = property_encoding.get('contentType')
            headers = property_encoding.get('headers')

        if not allowed_content_types:
            default_content_type = self.get_default_content_type(schema)
            if default_content_type is not None:
                allowed_content_types = (default_content_type, )

        headers_type = None
        if headers is not None:
            headers_type = self.headers_factory.generate(headers)

        return PartType(
            self.property_factory.generate(schema),
            allowed_content_types=allowed_content_types,
            headers_type=headers_type
        )

    def _generate_array_property(self, schema, property_encoding=None):
        return types.ArrayType(
            item_type=self._generate_part(schema['items'], property_encoding=property_encoding),
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            unique_items=schema['uniqueItems'],
            min_items=schema.get('minItems'),
            max_items=schema.get('maxItems'),
            enum=schema.get('enum')
        )

    def _generate_property(self, schema, property_encoding=None):
        schema_type = schema.get('type')

        if schema_type == SCHEMA_TYPES.ARRAY:
            return self._generate_array_property(schema, property_encoding=property_encoding)
        else:
            return self._generate_part(schema, property_encoding=property_encoding)

    def _generate(self, schema, encoding=None):
        schema_properties = schema.get('properties', {})
        schema_required = schema.get('required')

        properties = {}
        required = set()
        for property_name, property_schema in iteritems(schema_properties):
            if property_schema['readOnly']:
                continue

            if schema_required and property_name in schema_required:
                required.add(property_name)

            property_encoding = None
            if encoding is not None:
                property_encoding = encoding.get(property_name)

            properties[property_name] = self._generate_property(
                property_schema, property_encoding=property_encoding)

        return types.ObjectType(
            properties=properties,
            required=required,
            additional_properties=False,
            enum=schema.get('enum'),
            min_properties=schema.get('minProperties'),
            max_properties=schema.get('maxProperties'),
            messages={
                'extra_properties': "Additional properties are not supported for multipart media."
                                    " The following additional properties were found: {0}"
            }
        )


class UrlencodedMediaTypeFactory(AbstractMediaTypeFactory):

    def _generate(self, schema, encoding=None):
        schema_properties = schema.get('properties', {})
        schema_required = schema.get('required', set())

        parameters = []
        for property_name, property_schema in iteritems(schema_properties):
            if property_schema['readOnly']:
                continue

            parameter_type = ParameterFactory.get_parameter_type(property_schema)

            if parameter_type is None:
                style = IdentityParameterStyle()
            else:
                property_encoding = None
                if encoding is not None:
                    property_encoding = encoding.get(property_name)

                style = PARAMETER_STYLES.FORM
                explode = True
                if property_encoding is not None:
                    style = property_encoding['style']
                    explode = property_encoding['explode']

                style = PARAMETER_STYLE_CLASSES.get(
                    (PARAMETER_LOCATIONS.QUERY, parameter_type, style),
                    IdentityParameterStyle
                )(explode)

            subtype = self.property_factory.generate(property_schema)

            parameters.append(ParameterType(
                subtype=subtype,
                name=property_name,
                style=style,
                required=property_name in schema_required,
                allow_empty=False
            ))

        return ParametersType(parameters)


class RequestMediaTypeFactory(object):

    def __init__(self, property_factory, headers_factory):
        self.property_factory = property_factory
        self.urlencoded_media_type_factory = UrlencodedMediaTypeFactory(property_factory)
        self.multipart_media_type_factory = MultipartMediaTypeFactory(property_factory, headers_factory)

    def generate(self, content_type, media_type):
        schema = media_type.get('schema')

        if schema is None:
            return types.AnyType()

        encoding = media_type.get('encoding')

        if 'multipart/form-data' in content_type:
            return self.multipart_media_type_factory.generate(schema, encoding=encoding)
        elif any(ct in content_type for ct in (
            'application/x-www-form-urlencoded',
            'application/x-url-encoded',
        )):
            return self.urlencoded_media_type_factory.generate(schema, encoding=encoding)
        else:
            return self.property_factory.generate(schema)


class ResponseMediaTypeFactory(object):

    def __init__(self, property_factory):
        self.property_factory = property_factory

    def generate(self, content_type, media_type):
        schema = media_type.get('schema')

        if schema is None:
            return types.AnyType()

        return self.property_factory.generate(schema)
