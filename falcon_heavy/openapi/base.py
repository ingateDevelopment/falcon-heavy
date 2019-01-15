from __future__ import unicode_literals

import re

from ..schema import types


class BaseOpenApiObjectType(types.ObjectType):

    __slots__ = []

    PATTERN_PROPERTIES = {
        re.compile(r'^x-'): types.AnyType()
    }

    ADDITIONAL_PROPERTIES = False
