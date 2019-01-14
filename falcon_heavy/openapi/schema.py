from itertools import chain

from six import iteritems, itervalues

from ..schema import types, exceptions, undefined

from .xml import Xml
from .external_documentation import ExternalDocumentation
from .enums import SCHEMA_TYPES
from .extensions import SpecificationExtensions


class PipelinedType(types.AbstractType):

    """Pipelined type sequentially execute unmarshalling and validation
    for each subtype. Each followed type get result of previous type and
    returns result of last type in pipeline.
    """

    __slots__ = [
        'types'
    ]

    def __init__(self, *args, **kwargs):
        self.types = args
        super(PipelinedType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        for t in self.types:
            cursor.value = t.unmarshal(cursor, context=context)

        return cursor.value


def make_ref(value):
    """
    Generates reference structure from flat string.

    :param value: Reference.
    :type value: basestring
    :return: Reference object.
    :rtype: dict
    """
    return {
        '$ref': value
    }


Discriminator = types.Schema(
    name='Discriminator',
    properties={
        'propertyName': types.StringType(required=True),
        'mapping': types.DictType(
            PipelinedType(
                types.StringType(min_length=1, postprocessor=make_ref),
                types.ObjectOrReferenceType(lambda: Schema)
            ),
            min_values=1
        )
    }
)


def items_validator(value):
    """
    Validates `items` property. `items` must be specified for `array` schema type.

    :param value: Schema object.
    :type value: Object
    """
    if SCHEMA_TYPES.ARRAY in value.get('type', '') and 'items' not in value:
        raise exceptions.ValidationError(
            "`items` MUST be specified for `array` type")


def required_validator(value):
    """
    Validates `required` property. `required` has the meaning only if `properties` are specified.

    :param value: Schema object.
    :type value: Object
    """
    if 'required' in value and 'properties' not in value:
        raise exceptions.ValidationError(
            "`required` MAY be specified only if `properties` are specified")


def discriminator_validator(value):
    """
    Validates `discriminator` property. It has the meaning only with `oneOf` and `anyOf`.
    If `discriminator` was specified in schema with type `object`, then validates subschemas defined
    in `mapping` of `discriminator`. They must have this schema at top of `allOf`.

    :param value: Schema object.
    :type value: Object
    """
    discriminator = value.get('discriminator')
    if discriminator is None:
        return

    if 'allOf' in value or 'not' in value:
        raise exceptions.ValidationError(
            "The discriminator can only be used with the keywords `anyOf` or `oneOf`")

    if SCHEMA_TYPES.OBJECT in value.get('type', ''):
        mapping = discriminator.get('mapping')
        if mapping is None:
            return

        for subschema in itervalues(mapping):
            if 'allOf' not in subschema or not subschema['allOf'][0] is value:
                raise exceptions.ValidationError(
                    "The schema `{}` is specified in discriminator "
                    "mapping but not inherit the super schema `{}`".format(
                        subschema.url,
                        value.url
                    ))


def _get_subschemas(schema, kw=None):
    """If `kw` is not specified and type of schema not defined, then returns subschemas from all
    available properties that contains subschemas. If `kw` is specified, then returns subschemas
    from property with this keyword, if possible. In another cases returns empty list.

    :param schema: Schema object
    :type schema: Object
    :param kw: Keyword of property that contains subschemas. Default: None.
    :type kw: basestring
    :return: List of subschemas
    :rtype: list
    """
    if kw is not None:
        return schema.get(kw, [])
    elif not schema.get('type'):
        return list(chain(*[schema.get(kw_, []) for kw_ in ('allOf', 'oneOf', 'anyOf', 'not')]))
    else:
        return []


def dependencies_validator(kw):
    """Prevents recursive dependencies of subschemas.

    :param kw: Keyword of property that contains subschemas.
    :type kw: basestring
    :return: validator
    """
    def validator(value):
        """The validator itself.

        :param value: Schema object.
        :type value: Object
        """
        subschemas = _get_subschemas(value, kw)

        while subschemas:
            for subschema in subschemas:
                if subschema.url == value.url:
                    raise exceptions.ValidationError("Has recursive dependency")

            subschemas = list(chain(*[_get_subschemas(subschema) for subschema in subschemas]))

    return validator


TYPE_SPECIFIC_KEYWORDS = {
    SCHEMA_TYPES.STRING: ('minLength', 'maxLength', 'pattern'),
    SCHEMA_TYPES.NUMBER: ('minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum' 'multipleOf'),
    SCHEMA_TYPES.OBJECT: ('properties', 'additionalProperties', 'minProperties', 'maxProperties', 'required'),
    SCHEMA_TYPES.ARRAY: ('items', 'minItems', 'maxItems', 'uniqueItems')
}


def inferred_type(data, value):
    """
    Resolves schema type by keywords specific for concrete types.

    :param data: Original data.
    :type data: dict
    :param value: Schema object.
    :type value: Object
    :return: Inferred types.
    :rtype: basestring | list of basestring | UndefinedType
    """
    inferred = []
    for type_, keywords in iteritems(TYPE_SPECIFIC_KEYWORDS):
        if any(keyword for keyword in keywords if keyword in data):
            inferred.append(type_)

    if len(inferred) > 1:
        return inferred

    elif inferred:
        return inferred[0]

    return undefined.Undefined


def setdefaultattr(obj, name, value):
    try:
        return getattr(obj, name)
    except AttributeError:
        setattr(obj, name, value)
    return value


def model_level_polymorphism_support(value):
    """
    Adding current schema as subschema to super schema. Super schema must contains `discriminator` property.
    This works only for schemas that specified in components.

    :param value: Schema object.
    :type value: Object
    :return: Original value without any modifications.
    :rtype: Object
    """
    all_of = value.get('allOf')

    if all_of is None:
        return value

    if 'discriminator' in all_of[0]:
        setdefaultattr(all_of[0], 'subschemas', []).append(value)

    return value


Schema = types.Schema(
    name='Schema',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'type': types.StringType(enum=SCHEMA_TYPES),
        'title': types.StringType(),
        'multipleOf': types.FloatType(minimum=0, exclusive_minimum=True),
        'minimum': types.FloatType(),
        'maximum': types.FloatType(),
        'exclusiveMinimum': types.BooleanType(default=False),
        'exclusiveMaximum': types.BooleanType(default=False),

        'minLength': types.IntegerType(minimum=0, default=0),
        'maxLength': types.IntegerType(minimum=0),
        'pattern': types.PatternType(),

        'enum': types.ArrayType(types.AnyType(), min_items=1, unique_items=True),
        'allOf': types.ArrayType(types.ObjectOrReferenceType(lambda: Schema), min_items=1),
        'anyOf': types.ArrayType(types.ObjectOrReferenceType(lambda: Schema), min_items=1),
        'oneOf': types.ArrayType(types.ObjectOrReferenceType(lambda: Schema), min_items=1),
        'not': types.ArrayType(
            types.ObjectOrReferenceType(lambda: Schema),
            min_items=1
        ),

        'items': types.ObjectOrReferenceType(lambda: Schema),
        'minItems': types.IntegerType(minimum=0, default=0),
        'maxItems': types.IntegerType(minimum=0),
        'uniqueItems': types.BooleanType(default=False),

        'required': types.ArrayType(types.StringType(), min_items=1, unique_items=True),
        'properties': types.DictType(
            types.ObjectOrReferenceType(lambda: Schema)),
        'maxProperties': types.IntegerType(minimum=0),
        'minProperties': types.IntegerType(minimum=0, default=0),
        'additionalProperties': types.OneOfType([
            types.BooleanType(),
            types.ObjectOrReferenceType(lambda: Schema)
        ], default=True),

        'description': types.StringType(),
        'format': types.StringType(),
        'default': types.AnyType(),

        'nullable': types.BooleanType(default=False),
        'discriminator': types.ObjectType(Discriminator),
        'readOnly': types.BooleanType(default=False),
        'writeOnly': types.BooleanType(default=False),
        'xml': types.ObjectType(Xml),
        'externalDocs': types.ObjectType(ExternalDocumentation),
        'example': types.AnyType(),
        'deprecated': types.BooleanType(default=False)
    },
    validators={
        'items': items_validator,
        'required': required_validator,
        'discriminator': discriminator_validator,
        'allOf': dependencies_validator('allOf'),
        'oneOf': dependencies_validator('oneOf'),
        'anyOf': dependencies_validator('anyOf'),
        'not': dependencies_validator('not')
    },
    defaults={
        'type': inferred_type
    }
)
