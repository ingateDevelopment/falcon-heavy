from __future__ import unicode_literals

import os
from collections import namedtuple

from six import iteritems

from ..openapi.enums import (
    SCHEMA_TYPES,
    SCHEMA_FORMATS
)

from ..schema import types
from ..schema.undefined import Undefined

from .registry import registered, hashkey


PRIMITIVE_SCHEMA_TYPES = {
    SCHEMA_TYPES.INTEGER,
    SCHEMA_TYPES.NUMBER,
    SCHEMA_TYPES.STRING,
    SCHEMA_TYPES.BOOLEAN
}


PROPERTY_GENERATION_MODE = namedtuple(
    'PROPERTY_GENERATION_MODE',
    ['READ_WRITE', 'READ_ONLY', 'WRITE_ONLY']
)(
    READ_WRITE='rw',
    READ_ONLY='r',
    WRITE_ONLY='w'
)


class PropertyFactory(object):

    def __init__(self, mode=PROPERTY_GENERATION_MODE.READ_WRITE):
        self.mode = mode

    @classmethod
    def _generate_integer(cls, schema, type_class=types.IntegerType):
        return type_class(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            minimum=schema.get('minimum'),
            maximum=schema.get('maximum'),
            exclusive_minimum=schema.get('exclusiveMinimum'),
            exclusive_maximum=schema.get('exclusiveMaximum'),
            multiple_of=schema.get('multipleOf'),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_int32(cls, schema):
        return cls._generate_integer(schema, type_class=types.Int32Type)

    @classmethod
    def _generate_int64(cls, schema):
        return cls._generate_integer(schema, type_class=types.Int64Type)

    @classmethod
    def _generate_number(cls, schema):
        return types.NumberType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            minimum=schema.get('minimum'),
            maximum=schema.get('maximum'),
            exclusive_minimum=schema.get('exclusiveMinimum'),
            exclusive_maximum=schema.get('exclusiveMaximum'),
            multiple_of=schema.get('multipleOf'),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_string(cls, schema):
        return types.StringType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            min_length=schema.get('minLength'),
            max_length=schema.get('maxLength'),
            enum=schema.get('enum'),
            pattern=schema.get('pattern')
        )

    @classmethod
    def _generate_boolean(cls, schema):
        return types.BooleanType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_date(cls, schema):
        return types.DateType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_datetime(cls, schema):
        return types.DateTimeType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_uuid(cls, schema):
        return types.UUIDType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    @classmethod
    def _generate_base64(cls, schema):
        return types.Base64Type(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined)
        )

    @classmethod
    def _generate_binary(cls, schema):
        return types.BinaryType(
            nullable=schema['nullable']
        )

    @classmethod
    def _get_primitive_factory(cls, schema):
        schema_type = schema.get('type')
        schema_format = schema.get('format')

        factories = {
            (SCHEMA_TYPES.INTEGER, SCHEMA_FORMATS.INT32): cls._generate_int32,
            (SCHEMA_TYPES.INTEGER, SCHEMA_FORMATS.INT64): cls._generate_int64,
            (SCHEMA_TYPES.INTEGER, None): cls._generate_integer,
            (SCHEMA_TYPES.NUMBER, SCHEMA_FORMATS.FLOAT): cls._generate_number,
            (SCHEMA_TYPES.NUMBER, SCHEMA_FORMATS.DOUBLE): cls._generate_number,
            (SCHEMA_TYPES.NUMBER, None): cls._generate_number,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.BYTE): cls._generate_base64,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.BINARY): cls._generate_binary,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.DATE): cls._generate_date,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.DATETIME): cls._generate_datetime,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.PASSWORD): cls._generate_string,
            (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.UUID): cls._generate_uuid,
            (SCHEMA_TYPES.STRING, None): cls._generate_string,
            (SCHEMA_TYPES.BOOLEAN, None): cls._generate_boolean
        }

        return factories.get((schema_type, schema_format)) or factories.get((schema_type, None))

    def _generate_array(self, schema):
        return types.ArrayType(
            item_type=self.generate(schema['items']),
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            unique_items=schema['uniqueItems'],
            min_items=schema.get('minItems'),
            max_items=schema.get('maxItems'),
            enum=schema.get('enum')
        )

    def _generate_object(self, schema):
        schema_properties = schema.get('properties', {})
        schema_required = schema.get('required')

        properties = {}
        required = None
        if schema_required is not None:
            required = set(schema_required)
        for property_name, property_schema in iteritems(schema_properties):
            discard = ((property_schema['readOnly'] and self.mode == PROPERTY_GENERATION_MODE.WRITE_ONLY) or
                       (property_schema['writeOnly'] and self.mode == PROPERTY_GENERATION_MODE.READ_ONLY))
            if discard and required is not None:
                required.discard(property_name)
            elif not discard:
                properties[property_name] = self.generate(property_schema)

        additional_properties = schema['additionalProperties']
        if not isinstance(additional_properties, bool):
            additional_properties = self.generate(additional_properties)

        return types.ObjectType(
            properties=properties,
            required=required,
            additional_properties=additional_properties,
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum'),
            min_properties=schema.get('minProperties'),
            max_properties=schema.get('maxProperties')
        )

    def _generate_polymorphic(self, discriminator, subschemas):
        subschemas = {subschema.name: self.generate(subschema) for subschema in subschemas}
        mapping = {}
        for name, subschema in iteritems(subschemas):
            mapping[name] = subschema

        if 'mapping' in discriminator:
            for value, name in iteritems(discriminator['mapping']):
                if name in subschemas:
                    mapping[value] = subschemas[name]

        return types.DiscriminatorType(
            property_name=discriminator['propertyName'],
            mapping=mapping
        )

    def _generate_discriminator(self, discriminator, subschemas):
        subschemas = {subschema.ref: self.generate(subschema)
                      for subschema in subschemas
                      if subschema.ref is not None}
        mapping = {}
        for ref, subschema in iteritems(subschemas):
            mapping[os.path.splitext(os.path.basename(ref))[0]] = subschema

        if 'mapping' in discriminator:
            for value, ref in iteritems(discriminator['mapping']):
                if ref in subschemas:
                    mapping[value] = subschemas[ref]

        return types.DiscriminatorType(
            property_name=discriminator['propertyName'],
            mapping=mapping
        )

    def _generate_allof(self, schema):
        return types.AllOfType(
            subtypes=[self.generate(subschema, allow_model_level_polymorphic=bool(i))
                      for i, subschema in enumerate(schema['allOf'])],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    def _generate_anyof(self, schema):
        return types.AnyOfType(
            subtypes=[self.generate(subschema) for subschema in schema['anyOf']],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    def _generate_oneof(self, schema):
        return types.OneOfType(
            subtypes=[self.generate(subschema) for subschema in schema['oneOf']],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    def _generate_not(self, schema):
        return types.NotType(
            subtypes=[self.generate(subschema) for subschema in schema['not']]
        )

    @classmethod
    def _generate_any(cls, schema):
        return types.AnyType(
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum')
        )

    @registered(key=lambda schema, allow_model_level_polymorphic=True: hashkey(
        schema.path, allow_model_level_polymorphic=allow_model_level_polymorphic))
    def generate(self, schema, allow_model_level_polymorphic=True):
        schema_type = schema.get('type')

        primitive_factory = self._get_primitive_factory(schema)

        if primitive_factory is not None:
            return primitive_factory(schema)

        elif schema_type == SCHEMA_TYPES.ARRAY:
            return self._generate_array(schema)

        elif (
                schema_type == SCHEMA_TYPES.OBJECT and
                'discriminator' in schema and
                schema.subschemas and
                allow_model_level_polymorphic
        ):
            return self._generate_polymorphic(schema['discriminator'], schema.subschemas)

        elif schema_type == SCHEMA_TYPES.OBJECT:
            return self._generate_object(schema)

        elif 'discriminator' in schema and 'anyOf' in schema:
            return self._generate_discriminator(schema['discriminator'], schema['anyOf'])

        elif 'discriminator' in schema and 'oneOf' in schema:
            return self._generate_discriminator(schema['discriminator'], schema['oneOf'])

        elif 'allOf' in schema:
            return self._generate_allof(schema)

        elif 'anyOf' in schema:
            return self._generate_anyof(schema)

        elif 'oneOf' in schema:
            return self._generate_oneof(schema)

        elif 'not' in schema:
            return self._generate_not(schema)

        else:
            return self._generate_any(schema)
