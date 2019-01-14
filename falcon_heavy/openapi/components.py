import re

from six import iterkeys, iteritems

from ..schema import types, exceptions
from .schema import Schema, model_level_polymorphism_support
from .request_body import RequestBody
from .response import Response
from .parameter import Parameter
from .example import Example
from .header import Header
from .security_scheme import SecurityScheme
from .link import Link
from .callback import Callback
from .extensions import SpecificationExtensions


COMPONENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\.\-_]+$')


def component_names_validator(value):
    """
    Validates component names. Names must match to specific pattern.

    :param value: Any components.
    :type value: dict of Object
    """
    for k in iterkeys(value):
        if not COMPONENT_NAME_PATTERN.match(k):
            raise exceptions.SchemaError('Component has invalid name {0}'.format(k))


def set_names(value):
    """Sets the keys as object names.

    :param value: Any components.
    :type value: dict of Object
    """
    for k, v in iteritems(value):
        setattr(v, 'name', k)

    return value


Components = types.Schema(
    name='Components',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'schemas': types.DictType(
            types.ObjectOrReferenceType(Schema, postprocessor=model_level_polymorphism_support),
            validators=[component_names_validator],
            postprocessor=set_names
        ),
        'responses': types.DictType(
            types.ObjectOrReferenceType(Response),
            validators=[component_names_validator]
        ),
        'parameters': types.DictType(
            Parameter,
            validators=[component_names_validator]
        ),
        'examples': types.DictType(
            types.ObjectOrReferenceType(Example),
            validators=[component_names_validator]
        ),
        'requestBodies': types.DictType(
            types.ObjectOrReferenceType(RequestBody),
            validators=[component_names_validator]
        ),
        'headers': types.DictType(
            types.ObjectOrReferenceType(Header),
            validators=[component_names_validator]
        ),
        'securitySchemes': types.DictType(
            SecurityScheme,
            validators=[component_names_validator]
        ),
        'links': types.DictType(
            types.ObjectOrReferenceType(Link),
            validators=[component_names_validator]
        ),
        'callbacks': types.DictType(
            types.ObjectOrReferenceType(Callback),
            validators=[component_names_validator]
        )
    }
)
