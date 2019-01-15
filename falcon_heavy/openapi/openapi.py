from __future__ import unicode_literals

import re

from ..schema import types

from .base import BaseOpenApiObjectType
from .external_documentation import ExternalDocumentationObjectType
from .paths import PathsObjectType
from .info import InfoObjectType
from .security_requirement import SecurityRequirementObjectType
from .tag import TagObjectType
from .server import ServerObjectType
from .components import ComponentsObjectType


class OpenApiObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'openapi': types.StringType(pattern=re.compile(r'^3\.\d+\.\d+$')),
        'info': InfoObjectType(),
        'servers': types.ArrayType(ServerObjectType()),
        'paths': PathsObjectType(),
        'components': ComponentsObjectType(),
        'security': SecurityRequirementObjectType(),
        'tags': types.ArrayType(TagObjectType(), unique_items=True, unique_item_properties=['name']),
        'externalDocs': ExternalDocumentationObjectType()
    }

    REQUIRED = {
        'openapi',
        'info',
        'paths'
    }
