from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class ExternalDocumentationObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'description': types.StringType(),
        'url': types.UriType()
    }

    REQUIRED = {
        'url'
    }
