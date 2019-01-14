import re

from six import iterkeys

from ..schema import types, exceptions

from .external_documentation import ExternalDocumentation
from .parameter import Parameter
from .response import Response
from .request_body import RequestBody
from .callback import Callback
from .server import Server
from .extensions import SpecificationExtensions


HTTP_STATUS_CODE_PATTERN = re.compile(r'^[1-5](\d{2}|XX)$', re.IGNORECASE)
HTTP_STATUS_OK_PATTERN = re.compile(r'^2(\d{2}|XX)$', re.IGNORECASE)


def responses_validator(value):
    """
    Validates possible responses.

    :param value: Dictionary of possible responses.
    :type value: dict of Object
    """
    if not value:
        raise exceptions.ValidationError(
            "The Responses MUST contain at least one response code")

    if len(set(value.keys())) != len(value.keys()):
        raise exceptions.ValidationError(
            "Response codes MUST be unique")

    for key in iterkeys(value):
        if key != 'default' and not HTTP_STATUS_CODE_PATTERN.match(key):
            raise exceptions.ValidationError(
                "Invalid response key. MUST be `default` or HTTP status code")

    if len(value) == 1:
        key = list(value.keys())[0]
        if not HTTP_STATUS_OK_PATTERN.match(key):
            raise exceptions.ValidationError(
                "Responses SHOULD contains response for the successful operation call")


Operation = types.Schema(
    name='Operation',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'tags': types.ArrayType(types.StringType()),
        'summary': types.StringType(),
        'description': types.StringType(),
        'externalDocs': types.ObjectType(ExternalDocumentation),
        'operationId': types.StringType(),
        'parameters': types.ArrayType(
            Parameter,
            unique_items=True,
            key=lambda parameter: (parameter['name'], parameter['in'])
        ),
        'requestBody': types.ObjectOrReferenceType(RequestBody),
        'responses': types.DictType(
            types.ObjectOrReferenceType(Response),
            required=True,
            validators=[responses_validator]
        ),
        'callbacks': types.DictType(types.ObjectOrReferenceType(Callback)),
        'deprecated': types.BooleanType(default=False),
        'security': types.ArrayType(types.DictType(types.ArrayType(types.StringType(), default=[]))),
        'servers': types.ArrayType(types.ObjectType(Server))
    }
)
