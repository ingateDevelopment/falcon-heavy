from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class DiscriminatorObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'propertyName': types.StringType(min_length=1),
        'mapping': types.MapType(types.StringType(min_length=1))
    }

    REQUIRED = {
        'propertyName'
    }
