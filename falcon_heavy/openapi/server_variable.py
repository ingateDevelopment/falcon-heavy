from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class ServerVariableObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'enum': types.ArrayType(types.StringType()),
        'default': types.StringType(),
        'description': types.StringType()
    }

    REQUIRED = {
        'default'
    }
