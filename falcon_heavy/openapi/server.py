from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType
from .server_variable import ServerVariableObjectType


class ServerObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'url': types.StringType(),
        'description': types.StringType(),
        'variables': types.MapType(ServerVariableObjectType())
    }

    REQUIRED = {
        'url'
    }
