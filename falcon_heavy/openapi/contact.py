from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class ContactObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'name': types.StringType(),
        'url': types.UriType(),
        'email': types.EmailType()
    }
