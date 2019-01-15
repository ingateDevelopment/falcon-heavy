from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType
from .external_documentation import ExternalDocumentationObjectType


class TagObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'name': types.StringType(),
        'description': types.StringType(),
        'externalDocs': ExternalDocumentationObjectType()
    }

    REQUIRED = {
        'name'
    }
