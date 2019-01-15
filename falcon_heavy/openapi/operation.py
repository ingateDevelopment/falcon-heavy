from __future__ import unicode_literals

import warnings

from ..schema import types

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .external_documentation import ExternalDocumentationObjectType
from .parameter import ParameterPolymorphic
from .responses import ResponsesObjectType
from .request_body import RequestBodyObjectType
from .callback import CallbackObjectType
from .server import ServerObjectType


class OperationObjectType(BaseOpenApiObjectType):

    __slots__ = []

    MESSAGES = {
        'deprecated': "Operation '{0}' is deprecated"
    }

    PROPERTIES = {
        'tags': types.ArrayType(types.StringType()),
        'summary': types.StringType(),
        'description': types.StringType(),
        'externalDocs': ExternalDocumentationObjectType(),
        'operationId': types.StringType(),
        'parameters': types.ArrayType(
            ReferencedType(ParameterPolymorphic),
            unique_items=True,
            unique_item_properties=['in', 'name']
        ),
        'requestBody': ReferencedType(RequestBodyObjectType()),
        'responses': ResponsesObjectType(),
        'callbacks': types.MapType(ReferencedType(CallbackObjectType())),
        'deprecated': types.BooleanType(default=False),
        'security': types.ArrayType(types.MapType(types.ArrayType(types.StringType())), default=[]),
        'servers': types.ArrayType(ServerObjectType())
    }

    REQUIRED = {
        'responses'
    }

    def _convert(self, raw, path, **context):
        converted = super(OperationObjectType, self)._convert(raw, path, **context)

        if converted['deprecated']:
            warnings.warn(self.messages['deprecated'].format(path), DeprecationWarning)

        return converted
