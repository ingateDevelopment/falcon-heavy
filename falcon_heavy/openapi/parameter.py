from ..schema import types, exceptions, undefined

from .schema import Schema
from .example import Example
from .enums import PARAMETER_LOCATIONS, PARAMETER_STYLES
from .extensions import SpecificationExtensions


def only_one_entry_validator(value):
    """
    Validates that dictionary has only one key-value pair.

    :param value: Dictionary.
    :type value: Mapping
    """
    if value is not None and len(value) != 1:
        raise exceptions.ValidationError('MUST contains only one entry')


def allow_empty_value_validator(value):
    """
    Validates `allowEmptyValue` property. This keyword can be
    specified only for query-parameters.

    :param value: Parameter object.
    :type value: Object
    """
    if value['in'] != PARAMETER_LOCATIONS.QUERY and 'allowEmptyValue' in value:
        raise exceptions.ValidationError('This is valid only for query parameters')


BaseParameter = types.Schema(
    name='BaseParameter',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'name': types.StringType(required=True),
        'in': types.StringType(required=True, enum=PARAMETER_LOCATIONS),
        'description': types.StringType(),
        'required': types.BooleanType(default=False),
        'deprecated': types.BooleanType(default=False),
        'allowEmptyValue': types.BooleanType(),
        'style': types.StringType(enum=PARAMETER_STYLES),
        'explode': types.BooleanType(),
        'allowReserved': types.BooleanType(
            default=False,
            enum=[False],
            messages={'enum': "`allowReserved` permanently unsupported"}
        ),
        'schema': types.ObjectOrReferenceType(Schema),
        'example': types.AnyType(),
        'examples': types.DictType(types.ObjectOrReferenceType(Example)),
        'content': types.DictType(types.ObjectType(lambda: MediaType), validators=[only_one_entry_validator])
    },
    validators={
        'allowEmptyValue': allow_empty_value_validator
    },
    defaults={
        'explode': lambda data, value: value['style'] == PARAMETER_STYLES.FORM,
        'allowEmptyValue': (
            lambda data, value: False if value['in'] == PARAMETER_LOCATIONS.QUERY else undefined.Undefined)
    }
)


PathParameter = types.Schema(
    name='PathParameter',
    bases=BaseParameter,
    properties={
        'required': types.BooleanType(
            required=True,
            enum=[True],
            messages={'enum': "For path parameter this property MUST be TRUE"}
        ),
        'style': types.StringType(default=PARAMETER_STYLES.SIMPLE, enum=PARAMETER_STYLES)
    }
)


QueryParameter = types.Schema(
    name='QueryParameter',
    bases=BaseParameter,
    properties={
        'style': types.StringType(default=PARAMETER_STYLES.FORM, enum=PARAMETER_STYLES)
    }
)


HeaderParameter = types.Schema(
    name='HeaderParameter',
    bases=BaseParameter,
    properties={
        'style': types.StringType(default=PARAMETER_STYLES.SIMPLE, enum=PARAMETER_STYLES)
    }
)


CookieParameter = types.Schema(
    name='CookieParameter',
    bases=BaseParameter,
    properties={
        'schema': types.ObjectOrReferenceType(Schema, required=True),
        'style': types.StringType(default=PARAMETER_STYLES.FORM, enum=PARAMETER_STYLES)
    }
)


Parameter = types.OneOfType(
    property_types=[],
    discriminator=types.Discriminator(
        property_name='in',
        mapping={
            'path': types.ObjectOrReferenceType(PathParameter),
            'query': types.ObjectOrReferenceType(QueryParameter),
            'header': types.ObjectOrReferenceType(HeaderParameter),
            'cookie': types.ObjectOrReferenceType(CookieParameter)
        }
    )
)


from .media_type import MediaType  # noqa
