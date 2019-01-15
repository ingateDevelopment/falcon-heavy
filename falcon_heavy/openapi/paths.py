from __future__ import unicode_literals

import re

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .path_item import PathItemObjectType


class PathsObjectType(BaseOpenApiObjectType):

    __slots__ = []

    MESSAGES = {
        'extra_properties': "Paths must be starts with slash."
                            " The following invalid paths were found: {0}"
    }

    PATTERN_PROPERTIES = {
        re.compile(r'^/'): ReferencedType(PathItemObjectType())
    }
