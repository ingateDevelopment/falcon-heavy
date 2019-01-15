from __future__ import unicode_literals

import warnings

from six import iteritems

from wrapt import ObjectProxy

from .._compat import Mapping

from ..schema import types
from ..schema.exceptions import SchemaError, Error

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .xml import XmlObjectType
from .external_documentation import ExternalDocumentationObjectType
from .discriminator import DiscriminatorObjectType
from .enums import SCHEMA_TYPES


class ReferencedObjectProxy(ObjectProxy):

    __slots__ = ['_self_ref']

    def __init__(self, wrapped, ref=None):
        super(ReferencedObjectProxy, self).__init__(wrapped)
        self._self_ref = ref

    @property
    def ref(self):
        return self._self_ref

    @ref.setter
    def ref(self, value):
        self._self_ref = value


class ReferenceSaverType(types.AbstractConvertible):

    __slots__ = ['subtype']

    def __init__(self, subtype, **kwargs):
        self.subtype = subtype
        super(ReferenceSaverType, self).__init__(**kwargs)

    def convert(self, raw, path, **context):
        ref = None
        if isinstance(raw, Mapping) and '$ref' in raw:
            ref = raw['$ref']

        return ReferencedObjectProxy(self.subtype.convert(raw, path, **context), ref)


class SchemaObjectProxy(ObjectProxy):

    __slots__ = [
        '_self_path',
        '_self_subschemas'
    ]

    def __init__(self, wrapped, path, subschemas=None):
        super(SchemaObjectProxy, self).__init__(wrapped)
        self._self_path = path
        self._self_subschemas = subschemas or []

    @property
    def path(self):
        return self._self_path

    @path.setter
    def path(self, value):
        self._self_path = value

    @property
    def subschemas(self):
        return self._self_subschemas

    @subschemas.setter
    def subschemas(self, value):
        self._self_subschemas = value


class SchemaObjectType(BaseOpenApiObjectType):

    __slots__ = []

    TYPE_SPECIFIC_KEYWORDS = {
        SCHEMA_TYPES.STRING: ('minLength', 'maxLength', 'pattern'),
        SCHEMA_TYPES.NUMBER: ('minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'),
        SCHEMA_TYPES.OBJECT: ('properties', 'required', 'additionalProperties', 'minProperties', 'maxProperties'),
        SCHEMA_TYPES.ARRAY: ('items', 'minItems', 'maxItems', 'uniqueItems')
    }

    MESSAGES = {
        'ambiguous_type': "Schema type is ambiguous defined",
        'deprecated': "The schema '{0}' is deprecated",
        'items_required_for_type_array': "`items` must be specified for array type",
        'invalid_type_for_minimum': "`minimum` can only be used for number types",
        'invalid_type_for_maximum': "`maximum` can only be used for number types",
        'must_be_greater_than_minimum':
            "The value of `maximum` must be greater than or equal to the value of `minimum`",
        'exclusive_minimum_required_minimum': "When `exclusiveMinimum` is set, `minimum` is required",
        'exclusive_maximum_required_maximum': "When `exclusiveMaximum` is set, `maximum` is required",
        'invalid_type_for_multiple_of': "`multipleOf` can only be used for number types",
        'invalid_type_for_min_length': "`minLength` can only be used for string types",
        'invalid_type_for_max_length': "`maxLength` can only be used for string types",
        'must_be_greater_than_min_length':
            "The value of `maxLength` must be greater than or equal to the `minLength` value",
        'invalid_type_for_min_items': "`minItems` can only be used for array types",
        'invalid_type_for_max_items': "`maxItems` can only be used for array types",
        'must_be_greater_than_min_items':
            "The value of `maxItems` must be greater than or equal to the value of `minItems`",
        'invalid_type_for_unique_items': "`uniqueItems` can only be used for array types",
        'invalid_type_for_properties': "`properties` can only be used for object types",
        'invalid_type_for_additional_properties': "`additionalProperties` can only be used for object types",
        'invalid_type_for_required': "`required` can only be used for object types",
        'invalid_type_for_min_properties': "`minProperties` can only be used for object types",
        'invalid_type_for_max_properties': "`maxProperties` can only be used for object types",
        'must_be_greater_than_min_properties':
            "The value of `maxProperties` must be greater than or equal to `minProperties`",
        'improperly_discriminator_usage': "The `discriminator` can only be used with the keywords `anyOf` or `oneOf`",
        'read_only_and_write_only_are_mutually_exclusive':
            "`readOnly` and` writeOnly` are mutually exclusive and cannot be set simultaneously"
    }

    PROPERTIES = {
        'type': types.StringType(enum=SCHEMA_TYPES),
        'format': types.StringType(),
        'title': types.StringType(),
        'description': types.StringType(),
        'default': types.AnyType(),
        'nullable': types.BooleanType(default=False),
        'enum': types.ArrayType(types.AnyType(), min_items=1, unique_items=True),

        'readOnly': types.BooleanType(default=False),
        'writeOnly': types.BooleanType(default=False),
        'xml': XmlObjectType(),
        'externalDocs': ExternalDocumentationObjectType(),
        'example': types.AnyType(),
        'deprecated': types.BooleanType(default=False),

        'multipleOf': types.NumberType(minimum=0, exclusive_minimum=True),
        'minimum': types.NumberType(),
        'maximum': types.NumberType(),
        'exclusiveMinimum': types.BooleanType(default=False),
        'exclusiveMaximum': types.BooleanType(default=False),

        'minLength': types.IntegerType(minimum=0, default=0),
        'maxLength': types.IntegerType(minimum=0),
        'pattern': types.PatternType(),

        'discriminator': types.LazyType(lambda: DiscriminatorObjectType()),
        'allOf': types.ArrayType(ReferencedType(types.LazyType(lambda: SchemaObjectType())), min_items=1),
        'anyOf': types.ArrayType(
            ReferenceSaverType(ReferencedType(types.LazyType(lambda: SchemaObjectType()))), min_items=1),
        'oneOf': types.ArrayType(
            ReferenceSaverType(ReferencedType(types.LazyType(lambda: SchemaObjectType()))), min_items=1),
        'not': types.ArrayType(ReferencedType(types.LazyType(lambda: SchemaObjectType())), min_items=1),

        'items': ReferencedType(types.LazyType(lambda: SchemaObjectType())),
        'minItems': types.IntegerType(minimum=0, default=0),
        'maxItems': types.IntegerType(minimum=0),
        'uniqueItems': types.BooleanType(default=False),

        'required': types.ArrayType(types.StringType(), min_items=1, unique_items=True),
        'properties': types.MapType(ReferencedType(types.LazyType(lambda: SchemaObjectType()))),
        'minProperties': types.IntegerType(minimum=0, default=0),
        'maxProperties': types.IntegerType(minimum=0),
        'additionalProperties': types.OneOfType([
            types.BooleanType(),
            ReferencedType(types.LazyType(lambda: SchemaObjectType()))
        ], default=True)
    }

    def _convert(self, raw, path, **context):
        converted = super(SchemaObjectType, self)._convert(raw, path, **context)

        if 'type' not in converted:
            inferred = []
            for type_, keywords in iteritems(self.TYPE_SPECIFIC_KEYWORDS):
                if any(keyword for keyword in keywords if keyword in raw):
                    inferred.append(type_)

            if len(inferred) > 1:
                raise SchemaError(Error(path, self.messages['ambiguous_type']))

            elif inferred:
                converted.properties['type'] = inferred[0]

        if converted['deprecated']:
            warnings.warn(self.messages['deprecated'].format(path), DeprecationWarning)

        return SchemaObjectProxy(converted, path)

    def validate_items(self, converted, raw):
        """Validates `items` property

        `items` must be specified for `array` schema type

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if converted.get('type') == SCHEMA_TYPES.ARRAY and 'items' not in converted:
            return self.messages['items_required_for_type_array']

    def validate_discriminator(self, converted, raw):
        """Validates `discriminator` property

         It has the meaning only with `oneOf` and `anyOf`

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        discriminator = converted.get('discriminator')
        if discriminator is None:
            return

        if 'allOf' in raw or 'not' in raw:
            return self.messages['improperly_discriminator_usage']

    def validate_minimum(self, converted, raw):
        """Validates `minimum` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'minimum' in raw and converted.get('type') not in (SCHEMA_TYPES.NUMBER, SCHEMA_TYPES.INTEGER):
            return self.messages['invalid_type_for_minimum']

    def validate_maximum(self, converted, raw):
        """Validates `maximum` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'maximum' not in raw:
            return

        if converted.get('type') not in (SCHEMA_TYPES.NUMBER, SCHEMA_TYPES.INTEGER):
            return self.messages['invalid_type_for_maximum']

        if 'minimum' in converted and converted['maximum'] < converted['minimum']:
            return self.messages['must_be_greater_than_minimum']

    def validate_exclusive_minimum(self, converted, raw):
        """Validates `exclusiveMinimum` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'exclusiveMinimum' in raw and 'minimum' not in raw:
            return self.messages['exclusive_minimum_required_minimum']

    def validate_exclusive_maximum(self, converted, raw):
        """Validates `exclusiveMaximum` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'exclusiveMaximum' in raw and 'maximum' not in raw:
            return self.messages['exclusive_maximum_required_maximum']

    def validate_multiple_of(self, converted, raw):
        """Validates `multipleOf` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'multipleOf' in raw and converted.get('type') not in (SCHEMA_TYPES.NUMBER, SCHEMA_TYPES.INTEGER):
            return self.messages['invalid_type_for_multiple_of']

    def validate_min_length(self, converted, raw):
        """Validates `minLength` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'minLength' in raw and converted.get('type') != SCHEMA_TYPES.STRING:
            return self.messages['invalid_type_for_min_length']

    def validate_max_length(self, converted, raw):
        """Validates `maxLength` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'maxLength' not in raw:
            return

        if converted.get('type') != SCHEMA_TYPES.STRING:
            return self.messages['invalid_type_for_max_length']

        if 'minLength' in converted and converted['maxLength'] < converted['minLength']:
            return self.messages['must_be_greater_than_min_length']

    def validate_min_items(self, converted, raw):
        """Validates `minItems` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'minItems' in raw and converted.get('type') != SCHEMA_TYPES.ARRAY:
            return self.messages['invalid_type_for_min_items']

    def validate_max_items(self, converted, raw):
        """Validates `maxItems` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'maxItems' not in raw:
            return

        if converted.get('type') != SCHEMA_TYPES.ARRAY:
            return self.messages['invalid_type_for_max_items']

        if 'minItems' in converted and converted['maxItems'] < converted['minItems']:
                return self.messages['must_be_greater_than_min_items']

    def validate_unique_items(self, converted, raw):
        """Validates `uniqueItems` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'uniqueItems' in raw and converted.get('type') != SCHEMA_TYPES.ARRAY:
            return self.messages['invalid_type_for_unique_items']

    def validate_properties(self, converted, raw):
        """Validates `properties` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'properties' in raw and converted.get('type') != SCHEMA_TYPES.OBJECT:
            return self.messages['invalid_type_for_properties']

    def validate_additional_properties(self, converted, raw):
        """Validates `additionalProperties` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'additionalProperties' in raw and converted.get('type') != SCHEMA_TYPES.OBJECT:
            return self.messages['invalid_type_for_additional_properties']

    def validate_required(self, converted, raw):
        """Validates `required` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'required' in raw and converted.get('type') != SCHEMA_TYPES.OBJECT:
            return self.messages['invalid_type_for_required']

    def validate_min_properties(self, converted, raw):
        """Validates `minProperties` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'minProperties' in raw and converted.get('type') != SCHEMA_TYPES.OBJECT:
            return self.messages['invalid_type_for_min_properties']

    def validate_max_properties(self, converted, raw):
        """Validates `maxProperties` property

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """
        if 'maxProperties' not in raw:
            return

        if converted.get('type') != SCHEMA_TYPES.OBJECT:
            return self.messages['invalid_type_for_max_properties']

        if 'minProperties' in converted and converted['maxProperties'] < converted['minProperties']:
            return self.messages['must_be_greater_than_min_properties']

    def validate_read_only_write_only(self, converted, raw):
        """Validates `readOnly` and `writeOnly` properties

        :param converted: schema object
        :type converted: Object
        :param raw: raw data
        :type raw: Mapping
        """

        if converted['readOnly'] and converted['writeOnly']:
            return self.messages['read_only_and_write_only_are_mutually_exclusive']
