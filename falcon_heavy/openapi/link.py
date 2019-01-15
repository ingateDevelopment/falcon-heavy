from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType
from .server import ServerObjectType


class LinkObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'operationRef': types.StringType(),
        'operationId': types.StringType(),
        'parameters': types.MapType(types.AnyType()),
        'requestBody': types.AnyType(),
        'description': types.StringType(),
        'server': ServerObjectType()
    }
