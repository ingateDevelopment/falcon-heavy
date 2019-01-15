from __future__ import unicode_literals

from collections import defaultdict

from six import iteritems

from .._compat import Mapping

from ..openapi.enums import SCHEMA_TYPES

from ..schema import types
from ..schema.exceptions import SchemaError, Error
from ..schema.undefined import Undefined

from .registry import registered, hashkey
from .media_deserializers import media_deserializers
from .parameter_styles import AbstractParameterStyle, PARAMETER_STYLE_CLASSES
from .enums import PARAMETER_TYPES


class ParametersType(types.AbstractType):

    MESSAGES = {
        'type': "Should be a mapping"
    }

    __slots__ = [
        'parameters'
    ]

    def __init__(self, parameters, **kwargs):
        super(ParametersType, self).__init__(**kwargs)
        self.parameters = parameters

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping):
            raise SchemaError(Error(path, self.messages['type']))

        converted = {}
        errors = []
        for parameter in self.parameters:
            try:
                converted[parameter.name] = parameter.convert(raw, path, **context)
            except SchemaError as e:
                errors.extend(e.errors)

        if errors:
            raise SchemaError(*errors)

        return converted


class ParameterType(types.AbstractConvertible):

    """Parameter type

    :param subtype: parameter subtype
    :type subtype: AbstractConvertible
    :param name: parameter name
    :type name: basestring
    :param style: parameter serialization style
    :type style: AbstractParameterStyle
    :param required: shows that parameter must be present in request parameters
    :type required: bool
    :param allow_empty: sets the ability to pass empty-valued parameters
    :type allow_empty: bool
    """

    MESSAGES = {
        'empty': "Value can't be empty",
        'required': "Missing required parameter",
        'not_deserialized': "Value does not deserialize"
    }

    __slots__ = [
        'subtype',
        'name',
        'style',
        'required',
        'allow_empty'
    ]

    def __init__(self, subtype, name, style, required=False, allow_empty=True, **kwargs):
        super(ParameterType, self).__init__(**kwargs)
        self.subtype = subtype
        self.name = name
        self.style = style
        self.required = required
        self.allow_empty = allow_empty

    def convert(self, raw, path, strict=True, **context):
        raw = self.style.extract(raw, self.name)

        path = path / self.name

        if raw is Undefined and self.required:
            raise SchemaError(Error(path, self.messages['required']))

        elif raw is not Undefined:
            if not raw and not self.allow_empty:
                raise SchemaError(Error(path, self.messages['empty']))

            try:
                raw = self.style.deserialize(raw)
            except Exception:
                raise SchemaError(Error(path, self.messages['not_deserialized']))

        return self.subtype.convert(raw, path, strict=False, **context)


class IdentityParameterStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, Undefined)

    def deserialize(self, raw):
        return raw


class MediaParameterStyle(AbstractParameterStyle):

    def __init__(self, deserializer, **kwargs):
        super(MediaParameterStyle, self).__init__(**kwargs)
        self.deserializer = deserializer

    def extract(self, params, name, default=Undefined):
        return params.get(name, Undefined)

    def deserialize(self, raw):
        return self.deserializer(raw)


class ParameterFactory(object):

    def __init__(self, property_factory):
        self.property_factory = property_factory

    @staticmethod
    def get_parameter_type(schema):
        schema_type = schema.get('type')
        if schema_type == SCHEMA_TYPES.ARRAY:
            return PARAMETER_TYPES.ARRAY

        elif schema_type == SCHEMA_TYPES.OBJECT:
            return PARAMETER_TYPES.OBJECT

        elif schema_type is not None:
            return PARAMETER_TYPES.PRIMITIVE

    @registered(key=lambda location, name, parameter: hashkey(location, name, parameter.path))
    def generate(self, location, name, parameter):
        if 'schema' in parameter:
            schema = parameter['schema']
            parameter_type = self.get_parameter_type(schema)

            if parameter_type is None:
                style = IdentityParameterStyle()
            else:
                style = PARAMETER_STYLE_CLASSES.get(
                    (location, parameter_type, parameter['style']),
                    IdentityParameterStyle
                )(parameter['explode'])

            subtype = self.property_factory.generate(schema)

        elif 'content' in parameter:
            content_type, media_type = parameter['content']
            schema = media_type.get('schema')
            if schema is None:
                subtype = types.AnyType()
            else:
                subtype = self.property_factory.generate(schema)

            deserializer = media_deserializers.find_by_media_type(content_type)
            if deserializer is None:
                style = IdentityParameterStyle()
            else:
                style = MediaParameterStyle(deserializer)

        else:
            style = IdentityParameterStyle()
            subtype = types.AnyType()

        return ParameterType(
            subtype=subtype,
            name=name,
            style=style,
            required=parameter['required'],
            allow_empty=parameter.get('allowEmptyValue', True)
        )


class ParametersFactory(object):

    def __init__(self, parameter_factory):
        self.parameter_factory = parameter_factory

    def generate(self, parameters):
        locations = defaultdict(list)
        if parameters:
            for parameter in parameters:
                locations[parameter['in']].append(parameter)

        properties = {}
        for location, parameters in iteritems(locations):
            properties[location] = ParametersType(
                parameters=[
                    self.parameter_factory.generate(parameter['in'], parameter['name'], parameter)
                    for parameter in parameters
                ]
            )

        return types.ObjectType(
            properties=properties
        )
