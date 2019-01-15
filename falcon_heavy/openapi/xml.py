from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class XmlObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'name': types.StringType(),
        'namespace': types.StringType(),
        'prefix': types.StringType(),
        'attribute': types.BooleanType(default=False),
        'wrapped': types.BooleanType(default=False)
    }
