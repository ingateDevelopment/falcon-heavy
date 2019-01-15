from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class ExampleObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'summary': types.StringType(),
        'description': types.StringType(),
        'value': types.AnyType(),
        'externalValue': types.StringType()
    }
