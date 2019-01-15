from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class OAuthFlowObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'authorizationUrl': types.StringType(),
        'tokenUrl': types.StringType(),
        'refreshUrl': types.StringType(),
        'scopes': types.MapType(types.StringType())
    }

    REQUIRED = {
        'authorizationUrl',
        'tokenUrl',
        'scopes'
    }
