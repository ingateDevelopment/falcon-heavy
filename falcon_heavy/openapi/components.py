from __future__ import unicode_literals

import re

from six import iterkeys, iteritems

from wrapt import ObjectProxy

from ..schema import types

from .base import BaseOpenApiObjectType
from .types import ReferencedType, RegisteredType
from .schema import SchemaObjectType
from .request_body import RequestBodyObjectType
from .response import ResponseObjectType
from .parameter import ParameterPolymorphic
from .example import ExampleObjectType
from .header import HeaderObjectType
from .security_scheme import SecuritySchemePolymorphic
from .link import LinkObjectType
from .callback import CallbackObjectType
from .enums import SCHEMA_TYPES


COMPONENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\.\-_]+$')


class NamedObjectProxy(ObjectProxy):

    __slots__ = [
        '_self_name'
    ]

    def __init__(self, wrapped, name):
        super(NamedObjectProxy, self).__init__(wrapped)
        self._self_name = name

    @property
    def name(self):
        return self._self_name

    @name.setter
    def name(self, value):
        self._self_name = value


class ComponentsMapType(types.MapType):

    __slots__ = []

    MESSAGES = {
        'has_invalid_names': "The following component names are invalid: {0}"
    }

    def _convert(self, raw, path, **context):
        converted = super(ComponentsMapType, self)._convert(raw, path, **context)

        wrapped = {}
        for k, v in iteritems(converted):
            wrapped[k] = NamedObjectProxy(v, k)

        return wrapped

    def validate_names(self, converted, raw):
        """Validates component names

        Names must match to specific pattern

        :param converted: components map
        :type converted: dict of Object
        :param raw: raw data
        :type raw: Mapping
        """
        invalid_names = []
        for name in iterkeys(converted):
            if not COMPONENT_NAME_PATTERN.match(name):
                invalid_names.append(name)

        if invalid_names:
            return self.messages['has_invalid_names'].format(', '.join(sorted(invalid_names)))


class ComponentsObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'schemas': ComponentsMapType(
            RegisteredType(ReferencedType(SchemaObjectType()))),
        'responses': ComponentsMapType(
            RegisteredType(ReferencedType(ResponseObjectType()))),
        'parameters': ComponentsMapType(
            RegisteredType(ReferencedType(ParameterPolymorphic))),
        'examples': ComponentsMapType(
            RegisteredType(ReferencedType(ExampleObjectType()))),
        'requestBodies': ComponentsMapType(
            RegisteredType(ReferencedType(RequestBodyObjectType()))),
        'headers': ComponentsMapType(
            RegisteredType(ReferencedType(HeaderObjectType()))),
        'securitySchemes': ComponentsMapType(
            RegisteredType(ReferencedType(SecuritySchemePolymorphic))),
        'links': ComponentsMapType(
            RegisteredType(ReferencedType(LinkObjectType()))),
        'callbacks': ComponentsMapType(
            RegisteredType(ReferencedType(CallbackObjectType())))
    }

    def _convert(self, raw, path, **context):
        converted = super(ComponentsObjectType, self)._convert(raw, path, **context)

        schemas = converted.get('schemas')
        if not schemas:
            return converted

        for name, schema in iteritems(schemas):
            all_of = schema.get('allOf')

            if all_of is None or schema.get('type') is not None:
                continue

            top_subschema = all_of[0]
            if top_subschema.get('type') == SCHEMA_TYPES.OBJECT and 'discriminator' in top_subschema:
                top_subschema.subschemas.append(schema)

        return converted
